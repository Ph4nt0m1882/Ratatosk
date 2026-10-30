from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ratatosk.db.session import async_session_maker

from .models import Conversation, Message


async def get_history_by_token(conversation_id: str, nb_token: int) -> list[Message]:
    async with async_session_maker() as session:
        cumul_cte = (
            select(
                Message,
                func.sum(func.coalesce(Message.token_count, 0))
                .over(order_by=(Message.created_at.desc(), Message.id.desc()))
                .label("cumul_token"),
            )
            .where(Message.conversation_id == conversation_id)
            .cte("cumul")
        )

        MessageAlias = aliased(Message, cumul_cte)

        stmt = (
            select(MessageAlias)
            .where(cumul_cte.c.cumul_token <= nb_token)
            .order_by(cumul_cte.c.created_at.asc(), cumul_cte.c.id.asc())
        )

        results = (await session.execute(stmt)).scalars().all()
        return list(results)


async def get_history_by_number(conversation_id: str, nb_message: int) -> list[Message]:
    async with async_session_maker() as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(nb_message)
        )

        results = (await session.execute(stmt)).scalars().all()
        return list(reversed(results))


async def get_history_since_analysis(conversation_id: str) -> list[Message]:
    async with async_session_maker() as session:
        stmt = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.id == conversation_id)
            .where(Message.created_at > Conversation.analyzed_at)
            .order_by(Message.created_at.desc(), Message.id.desc())
        )

        results = (await session.execute(stmt)).scalars().all()
        return list(reversed(results))


async def get_full_history(conversation_id: str) -> list[Message]:
    async with async_session_maker() as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )

        results = (await session.execute(stmt)).scalars().all()
        return list(results)


async def create_new_conversation(user_id: str, session: AsyncSession) -> str:
    conversation = Conversation(user_id=user_id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    return conversation.id


async def save_message(
    user_id: str,
    conversation_id: str | None,
    role: str,
    model: str,
    content: str,
    parts: list[dict] | None = None,
    token_count: int | None = None,
    cost: float | None = None,
) -> tuple[str, str]:
    async with async_session_maker() as session:
        if conversation_id is None:
            conversation_id = await create_new_conversation(user_id, session)

        message = Message(
            conversation_id=conversation_id,
            role=role,
            model=model,
            content=content,
            parts=parts,
            token_count=token_count,
            cost=cost,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)

        return conversation_id, message.id
