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


async def remove_conversation(id: str, user: User):
    async with async_session_maker() as session:
        stmt = select(Conversation).where(Conversation.id == id)
        conversation = (await session.execute(stmt)).scalar_one_or_none()

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        conv_attachment_ids = list(
            (
                await session.execute(
                    select(MessageAttachment.attachment_id)
                    .join(Message, Message.id == MessageAttachment.message_id)
                    .where(Message.conversation_id == id)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )

        await session.delete(conversation)
        await session.flush()

        if conv_attachment_ids:
            await remove_attachments(conv_attachment_ids, session)

        await session.commit()

        if conv_attachment_ids:
            idle_worker.mark_dirty(ATTACHMENT_PURGE_TASK)


async def remove_attachments(conv_attachment_ids: list, session: AsyncSession):
    retention_days = dynamic_settings.attachment_retention_days_on_delete
    expires_at = datetime.now(UTC) + timedelta(days=retention_days)

    conditions = [
        Attachment.id.in_(conv_attachment_ids),
        ~exists().where(MessageAttachment.attachment_id == Attachment.id),
    ]
    if dynamic_settings.keep_generated_attachments:
        conditions.append(Attachment.is_generated.is_(False))

    await session.execute(
        update(Attachment).where(*conditions).values(expires_at=expires_at)
    )
