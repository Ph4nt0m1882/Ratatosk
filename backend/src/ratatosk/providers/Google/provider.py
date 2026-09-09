from typing import AsyncIterator
from google import genai
from ratatosk.core.config import settings
from ratatosk.providers.base import BaseAIProvider, ChatMessage


class GoogleProvider(BaseAIProvider):
    """Provider for Google GenAI."""
    DEFAULT_MODEL = "gemini-3.6-flash"

    def __init__(self, api_key: str | None = None):
        key = api_key or settings.gemini_api_key
        if not key:
            raise ValueError("GEMINI_API_KEY is required for GoogleProvider")
        self.client = genai.Client(api_key=key)

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict]:
        """Convert ChatMessage to the format expected by Google GenAI."""
        contents = []
        for message in messages:
            role = "model" if message.role == "assistant" else message.role
            contents.append({"role": role, "parts": [{"text": message.content}]})
        return contents


    async def generate_text(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> str:
        target_model = model or self.DEFAULT_MODEL
        contents = self._convert_messages(messages)
        
        response = await self.client.aio.models.generate_content(
            model=target_model,
            contents=contents,
        )
        return response.text or ""
    async def stream_text(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        target_model = model or self.DEFAULT_MODEL
        contents = self._convert_messages(messages)
        response_stream = await self.client.aio.models.generate_content_stream(
            model=target_model,
            contents=contents,
        )
        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text
