from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


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
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat responses from the provider."""
