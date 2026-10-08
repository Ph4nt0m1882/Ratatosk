from collections.abc import AsyncIterator

from ratatosk.providers.google import GoogleProvider
from ratatosk.providers.provider import BaseProvider
from ratatosk.providers.schemas import ModelInfo


class RatatoskProvider(BaseProvider):
    def __init__(self):
        self.provider_id = "ratatosk"
        self.display_name = "Ratatosk"

        all_candidates: list[BaseProvider] = [
            GoogleProvider(),
        ]
        self._subproviders = [p for p in all_candidates if p.is_available()]
        self._models_cache: dict[str, BaseProvider] = {}

    def is_available(self) -> bool:
        return len(self._subproviders) > 0

    async def list_models(self) -> list[ModelInfo]:
        """List all available models from the subproviders."""
        unified_list: list[ModelInfo] = []
        self._models_cache.clear()

        for sub_p in self._subproviders:
            raw_models = await sub_p.list_models()

            models_iterable = (
                raw_models.values() if isinstance(raw_models, dict) else raw_models
            )

            for m in models_iterable:
                model_info = ModelInfo(
                    id=m["id"],
                    provider=sub_p.provider_id,
                    display_name=m.get("display_name", m["id"]),
                    tasks=m.get("tasks", ["text-generation"]),
                    tier=m.get("tier", "standard"),
                    context_window=m.get("limits", {}).get("context_window")
                    if "limits" in m
                    else m.get("context_window"),
                    is_recommended=m.get("is_recommended", False),
                )
                unified_list.append(model_info)
                self._models_cache[model_info.id] = sub_p

        return unified_list

    async def list_models_by_provider(self) -> dict[str, list[ModelInfo]]:
        """List all available models grouped by provider."""
        all_models = await self.list_models()
        grouped: dict[str, list[ModelInfo]] = {}
        for m in all_models:
            grouped.setdefault(m.provider, []).append(m)
        return grouped

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """automatically route the chat request to the appropriate subprovider based on the model."""
        if not self._models_cache:
            await self.list_models()
        target_provider = self._models_cache.get(model)
        if not target_provider:
            raise ValueError(
                f"Model '{model}' unknown or no available provider to handle it."
            )
        async for chunk in target_provider.chat_stream(
            model=model,
            messages=messages,
            temperature=temperature,
            system_prompt=system_prompt,
        ):
            yield chunk
