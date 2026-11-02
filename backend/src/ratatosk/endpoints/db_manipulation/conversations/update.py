from fastapi import HTTPException
from sqlalchemy import select

from ratatosk.db.models import Conversation, Message, User
from ratatosk.db.session import async_session_maker

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

        for key, value in clean_update.items():
            setattr(conversation, key, value)

        await session.commit()
        await session.refresh(conversation)

    return await get_conversation(id, user)


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
