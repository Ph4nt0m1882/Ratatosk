from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncIterator
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class BaseAIProvider(ABC):
    """Strict contract for all providers to implement."""

    @abstractmethod
    async def generate_text(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> str:
        """Generate text from a list of messages."""
        raise NotImplementedError

    @abstractmethod
    async def stream_text(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream text from a list of messages."""
        raise NotImplementedError
