from typing import Literal

from pydantic import BaseModel, Field

from ratatosk.providers.provider import (
    AutoMode,
    EcoMode,
    FixedMode,
    FullMode,
    HistoryMode,
    NoneMode,
)


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    conversation_id: str | None = None
    history_mode: Literal["eco", "auto", "full", "none", "fixed"] = "eco"
    fixed_history_count: int = Field(default=10, gt=0, le=200)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    def resolve_history_mode(self) -> HistoryMode:
        match self.history_mode:
            case "eco":
                return EcoMode()
            case "auto":
                return AutoMode()
            case "full":
                return FullMode()
            case "none":
                return NoneMode()
            case "fixed":
                return FixedMode(n=self.fixed_history_count)
