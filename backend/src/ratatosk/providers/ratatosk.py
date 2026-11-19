from collections.abc import AsyncIterator

from ratatosk.providers.google import GoogleProvider
from ratatosk.providers.provider import (
    BaseProvider,
    EcoMode,
    HistoryMode,
    SearchMode,
    StandardSearchMode,
)
from ratatosk.providers.schemas import ModelInfo, StreamEvent


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

    async def list_models(self, force_update: bool = False) -> list[ModelInfo]:
        """List all available models from the subproviders."""
        unified_list: list[ModelInfo] = []
        self._models_cache.clear()

        for sub_p in self._subproviders:
            try:
                raw_models = await sub_p.list_models(force_update=force_update)
            except TypeError:
                raw_models = await sub_p.list_models()

            models_iterable = (
                raw_models.values() if isinstance(raw_models, dict) else raw_models
            )

            for m in models_iterable:
                raw_desc = m.get("description")
                if isinstance(raw_desc, dict):
                    desc_map = {
                        str(k): str(v)
                        for k, v in raw_desc.items()
                        if isinstance(v, str) and v.strip()
                    }
                    desc_str = desc_map.get("en") or desc_map.get("fr")
                elif isinstance(raw_desc, str):
                    desc_map = None
                    desc_str = raw_desc
                else:
                    desc_map = None
                    desc_str = None

                pricing_dict = (
                    m.get("pricing") if isinstance(m.get("pricing"), dict) else {}
                )

                model_info = ModelInfo(
                    id=m["id"],
                    provider=sub_p.provider_id,
                    display_name=m.get("display_name", m["id"]),
                    icon=m.get("icon"),
                    category=m.get("category", "general"),
                    tasks=m.get("tasks", ["text-generation"]),
                    tier=m.get("tier", "standard"),
                    context_window=m.get("limits", {}).get("context_window")
                    if "limits" in m
                    else m.get("context_window"),
                    input_price_per_1m=pricing_dict.get("input_per_1m"),
                    output_price_per_1m=pricing_dict.get("output_per_1m"),
                    is_recommended=m.get("is_recommended", False),
                    description=desc_str,
                    descriptions=desc_map,
                    rank=int(m.get("rank", 999)),
                )
                unified_list.append(model_info)
                self._models_cache[model_info.id] = sub_p

        return unified_list

    async def list_models_by_provider(
        self, force_update: bool = False
    ) -> dict[str, list[ModelInfo]]:
        """List all available models grouped by provider."""
        all_models = await self.list_models(force_update=force_update)
        grouped: dict[str, list[ModelInfo]] = {}
        for m in all_models:
            grouped.setdefault(m.provider, []).append(m)
        return grouped

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        user_id: str | None = None,
        is_admin: bool = False,
        conversation_id: str | None = None,
        history_mode: HistoryMode = EcoMode(),
        search_mode: SearchMode = StandardSearchMode(),
        temperature: float = 0.7,
        enable_builtin_tools: bool = True,
        unlocked_tools: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """automatically route the chat request to the appropriate subprovider based on the model."""
        target_provider, clean_model = await self._get_provider_for_model(model)
        async for event in target_provider.chat_stream(
            model=clean_model,
            messages=messages,
            user_id=user_id,
            is_admin=is_admin,
            conversation_id=conversation_id,
            history_mode=history_mode,
            search_mode=search_mode,
            temperature=temperature,
            enable_builtin_tools=enable_builtin_tools,
            unlocked_tools=unlocked_tools,
        ):
            yield event

    async def calcul_price(
        self, model: str, token: int, is_input: bool = True
    ) -> float:
        target_provider, clean_model = await self._get_provider_for_model(model)
        return await target_provider.calcul_price(clean_model, token, is_input)

    async def _get_provider_for_model(self, model: str) -> tuple[BaseProvider, str]:
        """Route a model ID (or 'provider/model') to its BaseProvider in O(1)."""

        if "/" in model:
            provider, clean_model = model.split("/", 1)
            for sub_p in self._subproviders:
                if sub_p.provider_id == provider or sub_p.display_name == provider:
                    return sub_p, clean_model

        if model not in self._models_cache:
            await self.list_models()

        target_provider = self._models_cache.get(model)
        if not target_provider:
            raise ValueError(
                f"Model '{model}' unknown or no available provider to handle it."
            )
        return target_provider, model
