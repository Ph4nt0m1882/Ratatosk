from typing import Any, Literal

from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    provider: str
    display_name: str
    tasks: list[str] = ["text-generation"]
    tier: str = "standard"
    context_window: int | None = None
    is_recommended: bool = False


class ListModelsResponse(BaseModel):
    models: list[ModelInfo]


# ==================== SSE STREAM EVENTS ====================


class ThinkingEvent(BaseModel):
    type: Literal["thinking"] = "thinking"
    delta: str


class TextEvent(BaseModel):
    type: Literal["text"] = "text"
    delta: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    id: str | None = None
    name: str
    args: dict[str, Any] = {}


class AttachmentEvent(BaseModel):
    type: Literal["attachment"] = "attachment"
    id: str
    filename: str
    mime_type: str


class StreamUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    thoughts_tokens: int = 0
    cost: float = 0.0
    currency: str = "USD"


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    conversation_id: str | None = None
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    model: str
    usage: StreamUsage


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


type StreamEvent = (
    ThinkingEvent
    | TextEvent
    | ToolCallEvent
    | AttachmentEvent
    | DoneEvent
    | ErrorEvent
)
