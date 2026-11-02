import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from google import genai

from ratatosk.core.config import settings
from ratatosk.core.currency import currency_manager
from ratatosk.core.dynamic_settings import dynamic_settings
from ratatosk.db import save_message
from ratatosk.providers.provider import BaseProvider, EcoMode, HistoryMode
from ratatosk.providers.schemas import (
    DoneEvent,
    ErrorEvent,
    StreamEvent,
    StreamUsage,
    TextEvent,
    ThinkingEvent,
    ToolCallEvent,
)

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


def _to_google_parts(raw_parts: list[dict] | None, fallback_content: str) -> list[dict]:
    """Convert normalized Ratatosk DB parts into Google GenAI-compatible Part dicts."""
    if not raw_parts:
        return [{"text": str(fallback_content)}]

    google_parts: list[dict] = []
    for p in raw_parts:
        if not isinstance(p, dict):
            continue
        p_type = p.get("type")
        if p_type in ("thinking", "thought") or p.get("thought") is True:
            continue
        if p_type == "tool_call" and "name" in p:
            google_parts.append(
                {"function_call": {"name": p["name"], "args": p.get("args", {})}}
            )
        elif "function_call" in p:
            google_parts.append({"function_call": p["function_call"]})
        elif "function_response" in p:
            google_parts.append({"function_response": p["function_response"]})
        elif "text" in p and p["text"] is not None:
            google_parts.append({"text": str(p["text"])})

    return google_parts or [{"text": str(fallback_content)}]


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

    async def list_models(self) -> dict[str, Any] | list[dict[str, Any]]:
        registry = get_google_models_registry()
        return registry.get("models", {})

    def _adapt_context_for_google(
        self, context: dict[str, Any], messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        final_system_prompt = context.get("System prompts") or ""

        def _adapt_messages_for_google(raw_messages: list) -> list[dict[str, Any]]:
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

                parts = _to_google_parts(raw_parts, content)

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
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        conversation_id: str | None = None,
        history_mode: HistoryMode = EcoMode(),
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamEvent]:
        if not self.is_available():
            yield ErrorEvent(message="Google API key is not set.")
            return

        try:
            context = await self.generate_context(conversation_id, history_mode)
            contents, final_system_prompt = self._adapt_context_for_google(
                context, messages
            )

            config: dict[str, Any] = {
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

            full_thoughts = ""
            full_message = ""
            tool_calls_saved: list[dict[str, Any]] = []
            last_chunk = None

            async for chunk in response:
                last_chunk = chunk
                candidates = getattr(chunk, "candidates", None) or []
                parts = (
                    getattr(candidates[0].content, "parts", None)
                    if candidates and getattr(candidates[0], "content", None)
                    else None
                )

                if parts:
                    for part in parts:
                        is_thought = getattr(part, "thought", False) is True
                        part_text = getattr(part, "text", None)
                        fn_call = getattr(part, "function_call", None)

                        if is_thought and part_text:
                            full_thoughts += part_text
                            yield ThinkingEvent(delta=part_text)
                        elif fn_call is not None:
                            call_id = getattr(fn_call, "id", None)
                            call_name = getattr(fn_call, "name", "")
                            call_args = dict(getattr(fn_call, "args", None) or {})
                            tool_calls_saved.append(
                                {
                                    "type": "tool_call",
                                    "id": call_id,
                                    "name": call_name,
                                    "args": call_args,
                                }
                            )
                            yield ToolCallEvent(
                                id=call_id, name=call_name, args=call_args
                            )
                        elif part_text:
                            full_message += part_text
                            yield TextEvent(delta=part_text)
                elif getattr(chunk, "text", None):
                    full_message += chunk.text
                    yield TextEvent(delta=chunk.text)

        except Exception as exc:  # noqa: BLE001
            yield ErrorEvent(message=str(exc))
            return

        resolved_model = (
            getattr(last_chunk, "model_version", None) or model
            if last_chunk is not None
            else model
        )
        usage = getattr(last_chunk, "usage_metadata", None) if last_chunk else None
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        candidates_tokens = (usage.candidates_token_count or 0) if usage else 0
        thoughts_tokens = (usage.thoughts_token_count or 0) if usage else 0
        total_output_tokens = candidates_tokens + thoughts_tokens

        pricing_model = resolved_model
        models_catalog = await self.list_models()
        if isinstance(models_catalog, dict) and pricing_model not in models_catalog:
            pricing_model = model

        input_cost = await self.calcul_price(pricing_model, input_tokens, is_input=True)
        output_cost = await self.calcul_price(
            pricing_model, total_output_tokens, is_input=False
        )

        user_msg_id: str | None = None
        assistant_msg_id: str | None = None

        if last_chunk is not None and user_id is not None:
            user_msg = messages[-1] if messages else {}
            conversation_id, user_msg_id = await save_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role=user_msg.get("role", "user"),
                model=resolved_model,
                content=user_msg.get("content", ""),
                parts=user_msg.get("parts"),
                token_count=input_tokens,
                cost=input_cost,
            )

            assistant_parts: list[dict[str, Any]] = []
            if full_thoughts:
                assistant_parts.append({"type": "thinking", "text": full_thoughts})
            assistant_parts.extend(tool_calls_saved)
            assistant_parts.append({"type": "text", "text": full_message})

            _, assistant_msg_id = await save_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                model=resolved_model,
                content=full_message,
                parts=assistant_parts,
                token_count=total_output_tokens,
                cost=output_cost,
            )

        yield DoneEvent(
            conversation_id=conversation_id,
            user_message_id=user_msg_id,
            assistant_message_id=assistant_msg_id,
            model=resolved_model,
            usage=StreamUsage(
                input_tokens=input_tokens,
                output_tokens=candidates_tokens,
                thoughts_tokens=thoughts_tokens,
                cost=round(input_cost + output_cost, 8),
                currency=dynamic_settings.currency,
            ),
        )

    async def calcul_price(
        self, model: str, token: int, is_input: bool = True
    ) -> float:
        models_catalog = await self.list_models()
        model_data = (
            models_catalog.get(model)
            if isinstance(models_catalog, dict)
            else next((m for m in models_catalog if m.get("id") == model), None)
        )
        if not model_data or "pricing" not in model_data:
            return 0.0

        pricing = model_data["pricing"]
        rate = (
            (pricing.get("input_per_1m") or 0.0)
            if is_input
            else (pricing.get("output_per_1m") or 0.0)
        )
        total_cost = (rate / 1_000_000) * token

        return currency_manager.auto_convert(total_cost)
