import asyncio
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import delete, exists, or_, select, update

from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import (
    Attachment,
    Conversation,
    Message,
    MessageAttachment,
    User,
)
from ratatosk.db.session import async_session_maker
from ratatosk.file_manager import FileStorageManager

from .stats import ATTACHMENT_STATS_TASK

ATTACHMENT_PURGE_TASK = "attachments_purge"


async def delete_attachment(
    attachment_id: str, user: User, strict: bool = False
) -> dict[str, str | int]:
    """Soft-delete an attachment (or all copies sharing its blob when strict=True)."""
    if strict and not user.is_admin:
        raise HTTPException(
            status_code=403, detail="Strict deletion requires admin privileges"
        )

    async with async_session_maker() as session:
        attachment = await session.get(Attachment, attachment_id)

        if attachment is None:
            raise HTTPException(status_code=404, detail="Attachment not found")
        if attachment.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        if strict:
            conditions = [Attachment.id == attachment_id]
            if attachment.file_path:
                conditions.append(Attachment.file_path == attachment.file_path)
            if attachment.file_hash:
                conditions.append(Attachment.file_hash == attachment.file_hash)
            target_ids = list(
                (await session.execute(select(Attachment.id).where(or_(*conditions))))
                .scalars()
                .all()
            )
        else:
            target_ids = [attachment_id]

        await session.execute(
            update(Attachment)
            .where(Attachment.id.in_(target_ids))
            .values(expires_at=datetime.now(UTC))
        )
        await session.execute(
            delete(MessageAttachment).where(
                MessageAttachment.attachment_id.in_(target_ids)
            )
        )
        await session.commit()

    idle_worker.mark_dirty(ATTACHMENT_PURGE_TASK)
    idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)
    return {
        "status": "scheduled_for_purge",
        "id": attachment_id,
        "affected": len(target_ids),
    }


async def purge_expired_attachments() -> int:
    """Purge expired, unreferenced attachment rows and remove unshared disk blobs."""
    file_manager = FileStorageManager()
    now = datetime.now(UTC)

    async with async_session_maker() as session:
        active_conv_ref = (
            select(MessageAttachment.attachment_id)
            .join(Message, Message.id == MessageAttachment.message_id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                MessageAttachment.attachment_id == Attachment.id,
                Conversation.archived.is_(False),
            )
        )
        stmt = select(Attachment).where(
            Attachment.expires_at.is_not(None),
            Attachment.expires_at <= now,
            ~exists(active_conv_ref),
        )
        expired_rows = list((await session.execute(stmt)).scalars().all())
        if not expired_rows:
            return 0

        expired_ids = [a.id for a in expired_rows]
        await session.execute(
            delete(MessageAttachment).where(
                MessageAttachment.attachment_id.in_(expired_ids)
            )
        )

        candidate_paths: set[str] = set()
        for attachment in expired_rows:
            if attachment.file_path:
                candidate_paths.add(attachment.file_path)
            await session.delete(attachment)

        await session.commit()

        still_used_paths: set[str] = set()
        if candidate_paths:
            used_rows = await session.execute(
                select(Attachment.file_path)
                .where(Attachment.file_path.in_(candidate_paths))
                .distinct()
            )
            still_used_paths = {p for p in used_rows.scalars().all() if p}

    for fp in candidate_paths - still_used_paths:
        await asyncio.to_thread(file_manager.delete_file, fp)

    idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)
    return len(expired_rows)
