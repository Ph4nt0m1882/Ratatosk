from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ratatosk.core.security import get_current_user
from ratatosk.db.models import User
from ratatosk.providers import provider

from .models import ChatRequest

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/models")
async def get_models():
    return await provider.list_models()


@router.get("/models/providers")
async def get_models_by_id(provider_id: str | None = None):
    models = await provider.list_models_by_provider()

    if provider_id:
        if provider_id not in models:
            return {"error": f"Provider '{provider_id}' not found."}
        return models[provider_id]
    return models


@router.post("/stream")
async def chat(
    request: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
):
    return StreamingResponse(
        provider.chat_stream(
            model=request.model,
            messages=[m.model_dump() for m in request.messages],
            user_id=user.id,
            conversation_id=request.conversation_id,
        ),
        media_type="text/event-stream",
    )
