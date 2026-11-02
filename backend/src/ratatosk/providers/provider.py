from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from ratatosk.db import get_final_system_prompts
from ratatosk.db.history import (
    get_full_history,
    get_history_by_number,
    get_history_by_token,
    get_history_since_analysis,
)
from ratatosk.db.models import Conversation
from ratatosk.providers.schemas import StreamEvent


@dataclass(frozen=True)
class EcoMode:
    pass


@dataclass(frozen=True)
class AutoMode:
    pass


@dataclass(frozen=True)
class FullMode:
    pass


@dataclass(frozen=True)
class NoneMode:
    pass


@dataclass(frozen=True)
class FixedMode:
    n: int


type HistoryMode = EcoMode | AutoMode | FullMode | NoneMode | FixedMode


class BaseProvider(ABC):
    provider_id: str  # e.g., "openai", "anthropic", "google"
    display_name: str  # e.g., "OpenAI", "Anthropic", "Google"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (e.g., API key is set)."""

    @abstractmethod
    async def list_models(self) -> list[dict[str, any]]:
        """List available models from the provider."""

    @abstractmethod
    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        user_id: str | None = None,
        conversation_id: str | None = None,
        history_mode: HistoryMode = EcoMode(),
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamEvent]:
        """Stream structured chat events from the provider."""

    @abstractmethod
    async def calcul_price(
        self, model: str, token: int, is_input: bool = True
    ) -> float:
        """return the cost of a message in usd"""

    async def generate_context(
        self, conversation_id: str | None, history_mode: HistoryMode
    ) -> dict:
        """return the context of a conversation_id"""
        context = {}

        ## System prompts
        context["System prompts"] = await get_final_system_prompts()

        if conversation_id is not None:
            ## Message history
            match history_mode:
                case EcoMode():
                    context["history"] = await get_history_since_analysis(
                        conversation_id
                    )
                case AutoMode():
                    estimated_max_token = 1000
                    context["history"] = await get_history_by_token(
                        conversation_id, estimated_max_token
                    )
                case FullMode():
                    context["history"] = await get_full_history(conversation_id)
                case NoneMode():
                    context["history"] = []
                case FixedMode(n=limit):
                    context["history"] = await get_history_by_number(
                        conversation_id, limit
                    )

            ## AI notes & conversation title
            conv = await Conversation.get_by_id(conversation_id, ["title", "ai_notes"])
            context["conversation title"] = (
                conv["title"] if conv else "New Conversation"
            )
            context["AI notes"] = (conv["ai_notes"] or "") if conv else ""

        else:
            context["history"] = []
            context["conversation title"] = "New Conversation"
            context["AI notes"] = ""

        return context
