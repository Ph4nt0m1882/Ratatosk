from pydantic import BaseModel


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
