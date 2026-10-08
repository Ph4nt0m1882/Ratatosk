import json
from collections.abc import AsyncIterator

import httpx
from google import genai

from ratatosk.core.config import settings
from ratatosk.providers.provider import BaseProvider

GITHUB_RAW_URL = "https://raw.githubusercontent.com/Ph4nt0m1882/AI_registery/master/Google/google_ai_studio.json"


def get_google_models_registry(force_update: bool = False) -> dict:
    cache_file = settings.app_dir / "google_ai_studio.json"

    if cache_file.exists() and not force_update:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        response = httpx.get(GITHUB_RAW_URL, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return data
    except httpx.RequestError as e:
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(f"Failed to fetch Google AI Studio models registry: {e}")


class GoogleProvider(BaseProvider):
    def __init__(self):
        self.provider_id = "google"
        self.display_name = "Gemini"

        get_google_models_registry()  # Ensure the registry is fetched and cached
        self._client = None
        if self.is_available():
            self._client = genai.Client(api_key=settings.google_api_key)

    def is_available(self) -> bool:
        return bool(settings.google_api_key)

    async def list_models(self) -> list[dict[str, any]]:
        registry = get_google_models_registry()
        return registry.get("models", [])

    def _adapt_messages_for_google(
        self, messages: list[dict[str, any]], system_prompt: str | None = None
    ) -> tuple[list[dict[str, any]], str | None]:
        contents = []
        final_system_prompt = system_prompt

        for m in messages:
            role = m.get("role", "user")

            # 1. Extraction unified of the content parts (text, image, etc.)
            parts = m.get("parts") or [{"text": str(m.get("content", ""))}]

            # 2. manage sys prompt
            if role == "system":
                # get the text
                final_system_prompt = m.get("content") or parts[0].get("text", "")
                continue

            # 3. normalyze the role to match Google API expectations
            contents.append(
                {
                    "role": "model" if role == "assistant" else role,
                    "parts": parts,
                    "automatic_function_calling": {"disable": True},
                }
            )

        return contents, final_system_prompt

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, any]],
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:

        if not self.is_available():
            raise RuntimeError("Google API key is not set.")

        contents, final_system_prompt = self._adapt_messages_for_google(
            messages, system_prompt
        )

        config: dict[str, any] = {"temperature": temperature}
        if final_system_prompt:
            config["system_instruction"] = final_system_prompt

        response = await self._client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text
