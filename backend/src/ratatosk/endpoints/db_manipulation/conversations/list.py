from sqlalchemy import func, select

from ratatosk.db.models import Conversation, Message, User
from ratatosk.db.session import async_session_maker

from .models import ConversationMetadata


async def requests_conversations(
    user_id: str | None = None,
    only_not_archived: bool = True,
) -> list[ConversationMetadata]:

    async with async_session_maker() as session:
        stmt = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.archived,
                func.max(Message.created_at).label("last_message"),
                func.count(Message.id).label("nb_message"),
                Conversation.user_id.label("owner_id"),
                User.username.label("owner_name"),
            )
            .join(User, Conversation.user_id == User.id)
            .outerjoin(Message, Conversation.id == Message.conversation_id)
            .group_by(Conversation.id, User.username)
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
