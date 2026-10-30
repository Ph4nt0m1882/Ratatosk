from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    conversation_id: str | None = None
