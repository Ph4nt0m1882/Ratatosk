from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ratatosk.core.security import get_current_user
from ratatosk.db.models import User

from .export import export_conversation
from .get import get_conversation, get_messages_list
from .list import requests_conversations
from .models import (
    ConversationManager,
    ConversationMetadata,
    ConversationUpdate,
    MessageData,
    MessagesRequest,
)
from .remove import remove_conversation
from .update import update_anchor, update_conversation

router = APIRouter(prefix="/conversations", tags=["Conversation"])


@router.get("/list")
async def list_conversation(
    user: Annotated[User, Depends(get_current_user)],
    user_id: str | None = None,
    only_not_archived: bool = True,
) -> list[ConversationMetadata]:
    return await requests_conversations(user, user_id, only_not_archived)


@router.get("/manager")
async def conversation_manager(
    conversation_id: str,
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationManager:
    return await get_conversation(conversation_id, user)


@router.get("/messages")
async def get_messages(
    request: Annotated[MessagesRequest, Query()],
    user: Annotated[User, Depends(get_current_user)],
) -> list[MessageData]:
    return await get_messages_list(request, user)


@router.patch("")
async def patch_conversation(
    user: Annotated[User, Depends(get_current_user)],
    conversation_id: str,
    data: ConversationUpdate,
) -> ConversationManager:
    return await update_conversation(conversation_id, data, user)


@router.patch("/anchor")
async def patch_anchor(
    user: Annotated[User, Depends(get_current_user)],
    conversation_id: str,
    anchor_id: str | None = None,
) -> ConversationManager:
    return await update_anchor(conversation_id, anchor_id, user)


@router.delete("")
async def delete_conversation(
    user: Annotated[User, Depends(get_current_user)],
    conversation_id: str,
):
    return await remove_conversation(conversation_id, user)


@router.get("/export")
async def export_conversation_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    conversation_id: str,
):
    return await export_conversation(conversation_id, user)
