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
    description: str | None = None
    rank: int = 999


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


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    id: str | None = None
    name: str
    result: dict[str, Any] = {}


class AttachmentEvent(BaseModel):
    type: Literal["attachment"] = "attachment"
    id: str
    filename: str
    mime_type: str
    is_generated: bool = False
    external_uri: str | None = None


class ImageProgressEvent(BaseModel):
    type: Literal["image_progress"] = "image_progress"
    step: int
    total_steps: int
    progress: float
    model: str
    status: str | None = None
    preview_base64: str | None = None
    mime_type: str = "image/jpeg"


class SourceItem(BaseModel):
    kind: Literal["web", "attachment"]
    title: str
    url: str | None = None
    attachment_id: str | None = None
    mime_type: str | None = None
    queries: list[str] = []


class SourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    items: list[SourceItem] = []


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
    | ToolResultEvent
    | ImageProgressEvent
    | AttachmentEvent
    | SourcesEvent
    | DoneEvent
    | ErrorEvent
)
