from fastapi import HTTPException
from sqlalchemy import select

from ratatosk.db.models import Conversation, User
from ratatosk.db.session import async_session_maker


async def remove_conversation(id: str, user: User):
    async with async_session_maker() as session:
        stmt = select(Conversation).where(Conversation.id == id)
        conversation = (await session.execute(stmt)).scalar_one_or_none()

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        await session.delete(conversation)
        await session.commit()
