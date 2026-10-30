import json
from collections.abc import AsyncIterator

import httpx
from google import genai

from ratatosk.core.config import settings
from ratatosk.core.currency import currency_manager
from ratatosk.db import save_message
from ratatosk.providers.provider import BaseProvider, EcoMode, HistoryMode

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

        get_google_models_registry(
            force_update=True
        )  # Ensure the registry is fetched and cached
        self._client = None
        if self.is_available():
            self._client = genai.Client(api_key=settings.google_api_key)

    def is_available(self) -> bool:
        return bool(settings.google_api_key)

    async def list_models(self) -> list[dict[str, any]]:
        registry = get_google_models_registry()
        return registry.get("models", [])

    def _adapt_context_for_google(
        self, context: dict[str, any], messages: list[dict[str, any]]
    ) -> tuple[list[dict[str, any]], str | None]:
        final_system_prompt = context.get("System prompts") or ""

        def _adapt_messages_for_google(raw_messages: list) -> list[dict[str, any]]:
            nonlocal final_system_prompt
            adapted = []

            for m in raw_messages:
                if isinstance(m, dict):
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    raw_parts = m.get("parts")
                else:
                    role = m.role
                    content = m.content
                    raw_parts = m.parts

                parts = raw_parts or [{"text": str(content)}]

                if role == "system":
                    sys_text = content or parts[0].get("text", "")
                    final_system_prompt = (
                        f"{final_system_prompt}\n\n{sys_text}"
                        if final_system_prompt
                        else sys_text
                    )
                    continue

                adapted.append(
                    {
                        "role": "model" if role == "assistant" else role,
                        "parts": parts,
                    }
                )

            return adapted

        history = context.get("history") or []
        contents = _adapt_messages_for_google(history) + _adapt_messages_for_google(
            messages
        )

        title = context.get("conversation title", "New Conversation")
        ai_notes = context.get("AI notes", "")
        if ai_notes or (title and title != "New Conversation"):
            conv_block = (
                "<conversation_context>\n"
                f"Conversation title: {title}\n"
                f"Summary of previous exchanges (AI Notes):\n{ai_notes or 'None'}\n"
                "</conversation_context>"
            )
            final_system_prompt = (
                f"{final_system_prompt}\n\n{conv_block}"
                if final_system_prompt
                else conv_block
            )

        return contents, final_system_prompt or None

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, any]],
        user_id: str | None = None,
        conversation_id: str | None = None,
        history_mode: HistoryMode = EcoMode(),
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:

        if not self.is_available():
            raise RuntimeError("Google API key is not set.")

        context = await self.generate_context(conversation_id, history_mode)
        contents, final_system_prompt = self._adapt_context_for_google(
            context, messages
        )

        config: dict[str, any] = {
            "temperature": temperature,
            "automatic_function_calling": {"disable": True},
        }
        if final_system_prompt:
            config["system_instruction"] = final_system_prompt

        response = await self._client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )

        full_message = ""
        last_chunk = None
        async for chunk in response:
            last_chunk = chunk
            if chunk.text:
                full_message += chunk.text
                yield chunk.text

        if last_chunk is not None and user_id is not None:
            resolved_model = last_chunk.model_version or model
            usage = last_chunk.usage_metadata
            input_tokens = (usage.prompt_token_count or 0) if usage else 0
            output_tokens = (
                (
                    (usage.candidates_token_count or 0)
                    + (usage.thoughts_token_count or 0)
                )
                if usage
                else 0
            )

            user_msg = messages[-1] if messages else {}
            conversation_id, _ = await save_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role=user_msg.get("role", "user"),
                model=resolved_model,
                content=user_msg.get("content", ""),
                parts=user_msg.get("parts"),
                token_count=input_tokens,
                cost=await self.calcul_price(
                    resolved_model, input_tokens, is_input=True
                ),
            )

            await save_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                model=resolved_model,
                content=full_message,
                parts=[{"text": full_message}],
                token_count=output_tokens,
                cost=await self.calcul_price(
                    resolved_model, output_tokens, is_input=False
                ),
            )

    async def calcul_price(self, model, token, is_input=True):
        model_data = (await self.list_models())[model]

        pricing = model_data["pricing"]

        cost = pricing["input_per_1m"] if is_input else pricing["output_per_1m"] or 0.0
        total_cost = (cost / 1_000_000) * token

        return currency_manager.auto_convert(total_cost)
