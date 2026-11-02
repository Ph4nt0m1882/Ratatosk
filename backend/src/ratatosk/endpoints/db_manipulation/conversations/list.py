from fastapi import HTTPException
from sqlalchemy import func, select

from ratatosk.db.models import Conversation, Message, User
from ratatosk.db.session import async_session_maker

from .models import ConversationMetadata


async def requests_conversations(
    user: User,
    user_id: str | None = None,
    only_not_archived: bool = True,
) -> list[ConversationMetadata]:
    if not user.is_admin:
        if user_id is not None and user_id != user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        user_id = user.id

    async with async_session_maker() as session:
        last_msg_expr = func.max(Message.created_at)
        stmt = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.archived,
                last_msg_expr.label("last_message"),
                func.count(Message.id).label("nb_message"),
                Conversation.user_id.label("owner_id"),
                User.username.label("owner_name"),
            )
            .join(User, Conversation.user_id == User.id)
            .outerjoin(Message, Conversation.id == Message.conversation_id)
            .group_by(Conversation.id, User.username)
            .order_by(func.coalesce(last_msg_expr, Conversation.created_at).desc())
        )

        if user_id is not None:
            stmt = stmt.where(Conversation.user_id == user_id)
        if only_not_archived:
            stmt = stmt.where(~Conversation.archived)

        results = await session.execute(stmt)

    return [
        ConversationMetadata.model_validate(result)
        for result in results.mappings().all()
    ]
