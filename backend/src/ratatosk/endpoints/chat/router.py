from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from ratatosk.core.security import get_current_user
from ratatosk.db.models import Conversation, User
from ratatosk.providers import provider

from .models import ChatRequest

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/models")
async def get_models(refresh: bool = False):
    return await provider.list_models(force_update=refresh)


@router.get("/models/providers")
async def get_models_by_id(provider_id: str | None = None, refresh: bool = False):
    models = await provider.list_models_by_provider(force_update=refresh)

    if provider_id:
        if provider_id not in models:
            return {"error": f"Provider '{provider_id}' not found."}
        return models[provider_id]
    return models


@router.post("/stream")
async def chat(
    request: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    if request.conversation_id is not None:
        conv = await Conversation.get_by_id(request.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        await provider._get_provider_for_model(request.model)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def _sse_generator() -> AsyncIterator[dict[str, str]]:
        async for event in provider.chat_stream(
            model=request.model,
            messages=[m.model_dump() for m in request.messages],
            user_id=user.id,
            is_admin=user.is_admin,
            conversation_id=request.conversation_id,
            history_mode=request.resolve_history_mode(),
            search_mode=request.resolve_search_mode(),
            temperature=request.temperature,
            enable_builtin_tools=request.enable_builtin_tools,
            unlocked_tools=request.unlocked_tools,
        ):
            yield {"event": event.type, "data": event.model_dump_json()}

    return EventSourceResponse(_sse_generator())
