from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ratatosk.providers.base import ChatMessage
from ratatosk.providers.Google.provider import GoogleProvider

router = APIRouter(tags=["Chat"], prefix="/chat")

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None

class ChatResponse(BaseModel):
    response: str
    model: str

@router.post("", response_model=ChatResponse)
async def chat_generate(request: ChatRequest):
    """Génération textuelle classique (réponse complète d'un coup)."""
    try:
        provider = GoogleProvider()
        response_text = await provider.generate_text(
            messages=request.messages,
            model=request.model,
        )
        return ChatResponse(
            response=response_text,
            model=request.model or provider.DEFAULT_MODEL,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Génération textuelle en temps réel (SSE - Server-Sent Events)."""
    try:
        provider = GoogleProvider()

        async def event_generator():
            async for token in provider.stream_text(request.messages, request.model):
                # Format SSE standard attendu par Flutter
                yield {"data": token}

        return EventSourceResponse(event_generator())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))