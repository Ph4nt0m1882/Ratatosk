from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ratatosk.providers import provider

from .models import ChatRequest

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
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
async def chat(request: ChatRequest):
    return StreamingResponse(
        provider.chat_stream(model=request.model, messages=request.messages),
        media_type="text/event-stream",
    )
