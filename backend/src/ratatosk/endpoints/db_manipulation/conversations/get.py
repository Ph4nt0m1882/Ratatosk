from fastapi import HTTPException
from sqlalchemy import func, or_, select

from ratatosk.db.models import Conversation, Message, User
from ratatosk.db.session import async_session_maker

from .models import ConversationManager, MessageData, MessagesRequest, RefMessage


async def _get_authorized_conversation(conversation_id: str, user: User) -> Conversation:
    conv = await Conversation.get_by_id(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return conv


async def get_conversation(conversation_id: str, user: User) -> ConversationManager:
    conv = await _get_authorized_conversation(conversation_id, user)

    async with async_session_maker() as session:
        ranked = (
            select(
                Message.id,
                (
                    func.row_number().over(
                        order_by=(Message.created_at.asc(), Message.id.asc())
                    )
                    - 1
                ).label("msg_index"),
                func.count().over().label("nb_message"),
            )
            .where(Message.conversation_id == conversation_id)
            .cte("ranked")
        )

        stmt = (
            select(ranked.c.id, ranked.c.msg_index, ranked.c.nb_message)
            .where(
                or_(
                    ranked.c.id == conv.cache_anchor,
                    ranked.c.msg_index == ranked.c.nb_message - 1,
                )
            )
            .order_by(ranked.c.msg_index.asc())
            .limit(1)
        )

        row = (await session.execute(stmt)).first()

    return ConversationManager(
        id=conv.id,
        title=conv.title,
        title_auto=conv.title_auto,
        archived=conv.archived,
        anchor_message=row.id if row else None,
        anchor_message_index=row.msg_index if row else None,
        nb_message=row.nb_message if row else 0,
    )


async def get_messages_list(
    request: MessagesRequest, user: User
) -> list[MessageData]:
    await _get_authorized_conversation(request.conversation_id, user)

    if request.ref_message_id is not None:
        ref_msg = await Message.get_by_id(
            request.ref_message_id, fields=["conversation_id"]
        )
        if ref_msg is None or ref_msg["conversation_id"] != request.conversation_id:
            raise HTTPException(
                status_code=404,
                detail="Reference message not found in this conversation",
            )

    async with async_session_maker() as session:
        numbered = (
            select(
                Message.id,
                Message.role,
                Message.model,
                Message.content,
                Message.parts,
                Message.token_count,
                Message.cost,
                Message.created_at,
                (
                    func.row_number().over(
                        order_by=(Message.created_at.asc(), Message.id.asc())
                    )
                    - 1
                ).label("idx"),
                func.count().over().label("total"),
            )
            .where(Message.conversation_id == request.conversation_id)
            .cte("numbered")
        )

        stmt = select(
            numbered.c.id,
            numbered.c.role,
            numbered.c.model,
            numbered.c.content,
            numbered.c.parts,
            numbered.c.token_count,
            numbered.c.cost,
            numbered.c.created_at,
            (numbered.c.idx == 0).label("is_first"),
            (numbered.c.idx == numbered.c.total - 1).label("is_last"),
        )

        n = request.nb_requested
        if request.ref_message_id is None:
            # Default: last `n` messages of the conversation
            stmt = stmt.where(numbered.c.idx >= numbered.c.total - n)
        else:
            ref_idx = (
                select(numbered.c.idx)
                .where(numbered.c.id == request.ref_message_id)
                .scalar_subquery()
            )
            match request.ref_message:
                case RefMessage.AFTER:  # ref is previous -> get `n` messages AFTER it
                    stmt = stmt.where(numbered.c.idx.between(ref_idx + 1, ref_idx + n))
                case RefMessage.BEFORE:  # ref is next -> get `n` messages BEFORE it
                    stmt = stmt.where(numbered.c.idx.between(ref_idx - n, ref_idx - 1))
                case RefMessage.AROUND:  # centered around ref (included)
                    half = n // 2
                    stmt = stmt.where(
                        numbered.c.idx.between(ref_idx - half, ref_idx + (n - 1 - half))
                    )

        stmt = stmt.order_by(numbered.c.idx.asc())
        rows = (await session.execute(stmt)).mappings().all()

    return [MessageData.model_validate(row) for row in rows]
