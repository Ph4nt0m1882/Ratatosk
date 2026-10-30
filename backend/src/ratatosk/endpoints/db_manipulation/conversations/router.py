from fastapi import APIRouter

from .list import requests_conversations
from .models import ConversationMetadata

router = APIRouter(prefix="/conversations", tags=["Conversation"])


@router.get("/list")
async def list_conversation(
    user_id: str | None = None,
    only_not_archived: bool = True,
) -> list[ConversationMetadata]:
    return await requests_conversations(user_id, only_not_archived)
