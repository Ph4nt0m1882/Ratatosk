from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ratatosk.core.dynamic_settings import dynamic_settings
from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import (
    Attachment,
    Conversation,
    Message,
    MessageAttachment,
    User,
)
from ratatosk.db.session import async_session_maker
from ratatosk.endpoints.db_manipulation.attachments.remove import ATTACHMENT_PURGE_TASK

from .get import get_conversation
from .models import ConversationManager, ConversationUpdate


async def update_conversation(
    id: str, data: ConversationUpdate, user: User
) -> ConversationManager:
    clean_update = data.model_dump(exclude_none=True)

    async with async_session_maker() as session:
        stmt = select(Conversation).where(Conversation.id == id)
        conversation = (await session.execute(stmt)).scalar_one_or_none()

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        was_archived = conversation.archived
        for key, value in clean_update.items():
            setattr(conversation, key, value)

        archive_toggled = (
            "archived" in clean_update and conversation.archived != was_archived
        )
        if archive_toggled:
            await session.flush()
            await _sync_archive_attachments(id, conversation.archived, session)

        await session.commit()
        await session.refresh(conversation)

    if archive_toggled:
        idle_worker.mark_dirty(ATTACHMENT_PURGE_TASK)

    return await get_conversation(id, user)


async def _sync_archive_attachments(
    conversation_id: str, archived: bool, session: AsyncSession
) -> None:
    """Apply or clear attachment expiration when a conversation's archive state changes."""
    conv_attachment_ids = list(
        (
            await session.execute(
                select(MessageAttachment.attachment_id)
                .join(Message, Message.id == MessageAttachment.message_id)
                .where(Message.conversation_id == conversation_id)
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    if not conv_attachment_ids:
        return

    if not archived:
        await session.execute(
            update(Attachment)
            .where(Attachment.id.in_(conv_attachment_ids))
            .values(expires_at=None)
        )
        return

    if not dynamic_settings.expire_attachments_on_archive:
        return

    retention_days = dynamic_settings.attachment_retention_days_on_archive
    expires_at = datetime.now(UTC) + timedelta(days=retention_days)

    active_conv_ref = (
        select(MessageAttachment.attachment_id)
        .join(Message, Message.id == MessageAttachment.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            MessageAttachment.attachment_id == Attachment.id,
            Conversation.archived.is_(False),
        )
    )
    conditions = [
        Attachment.id.in_(conv_attachment_ids),
        ~exists(active_conv_ref),
    ]
    if dynamic_settings.keep_generated_attachments:
        conditions.append(Attachment.is_generated.is_(False))

    await session.execute(
        update(Attachment).where(*conditions).values(expires_at=expires_at)
    )


async def update_anchor(
    id: str, anchor_id: str | None, user: User
) -> ConversationManager:
    async with async_session_maker() as session:
        stmt = select(Conversation).where(Conversation.id == id)
        conversation = (await session.execute(stmt)).scalar_one_or_none()

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        if anchor_id is not None:
            stmt = (
                select(Message.id)
                .where(Message.id == anchor_id)
                .where(Message.conversation_id == id)
            )
            message_id = (await session.execute(stmt)).scalar_one_or_none()
            if message_id is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Message {anchor_id} not found in conversation {id}",
                )

        conversation.cache_anchor = anchor_id

        await session.commit()
        await session.refresh(conversation)

    return await get_conversation(id, user)
