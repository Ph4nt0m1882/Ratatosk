import asyncio
import base64
from datetime import datetime, timezone
import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from google import genai
from sqlalchemy import select

from ratatosk.core.config import settings
from ratatosk.core.currency import currency_manager
from ratatosk.core.dynamic_settings import dynamic_settings
from ratatosk.db import save_message
from ratatosk.db.models import Attachment
from ratatosk.db.session import async_session_maker
from ratatosk.file_manager import FileStorageManager
from ratatosk.providers.provider import (
    BaseProvider,
    EcoMode,
    FullSearchMode,
    HistoryMode,
    NoSearchMode,
    SearchMode,
    StandardSearchMode,
)
from ratatosk.providers.schemas import (
    AttachmentEvent,
    DoneEvent,
    ErrorEvent,
    ImageProgressEvent,
    SourceItem,
    SourcesEvent,
    StreamEvent,
    StreamUsage,
    TextEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from ratatosk.tools import (
    GENERATE_IMAGE_TOOL_NAME,
    IMAGE_GENERATION_TASK,
    DelegationModelCandidate,
    MCPToolBinding,
    ToolContext,
    ToolExecutionResult,
    build_generate_image_declaration,
    builtin_registry,
    discover_mcp_tools,
    execute_mcp_tool,
    extract_grounding_sources,
    fetch_and_store_web_image,
    find_grounding_insert_offset,
    resolve_delegation_models,
    stream_google_delegated_image,
)

GITHUB_REPO = "Ph4nt0m1882/AI_registery"
GITHUB_FILE_PATH = "Google/google_ai_studio.json"
GITHUB_COMMITS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/{GITHUB_FILE_PATH}"
REGISTRY_CHECK_TTL_SECONDS = 900.0  # Check GitHub at most every 15 minutes unless forced
MAX_TOOL_ROUNDS = 5

_registry_mem_cache: dict[str, Any] | None = None
_registry_file_mtime: float = 0.0
_registry_last_checked_ts: float = 0.0

FULL_SEARCH_DIRECTIVE = (
    "<search_directive>\n"
    "Deep Search mode is active. Base your response on thorough web research:\n"
    "1. Formulate multiple complementary search queries to explore all facets of the topic.\n"
    "2. Inspect relevant URLs in depth using url_context.\n"
    "3. Cross-verify facts across independent sources and synthesize a comprehensive answer.\n"
    "</search_directive>"
)


def _parse_iso_timestamp(value: str | None) -> float:
    if not value or not isinstance(value, str):
        return 0.0
    try:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def _load_registry_meta(meta_file) -> dict[str, Any]:
    if not meta_file.exists():
        return {}
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_registry_meta(meta_file, meta: dict[str, Any]) -> None:
    try:
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _check_github_file_commit(
    known_etag: str | None,
) -> tuple[str | None, str | None, str | None, bool]:
    """Query GitHub Commits API for the latest commit modifying Google/google_ai_studio.json.

    Returns (commit_sha, commit_date_iso, etag, is_not_modified).
    """
    headers = {"Accept": "application/vnd.github+json"}
    if known_etag:
        headers["If-None-Match"] = known_etag
    try:
        resp = httpx.get(
            GITHUB_COMMITS_URL,
            params={"path": GITHUB_FILE_PATH, "per_page": 1},
            headers=headers,
            timeout=5.0,
        )
        if resp.status_code == 304:
            return None, None, known_etag, True
        if resp.status_code == 200:
            commits = resp.json()
            new_etag = resp.headers.get("ETag") or known_etag
            if isinstance(commits, list) and commits:
                latest = commits[0]
                sha = latest.get("sha")
                commit_info = latest.get("commit", {})
                committer_date = (
                    commit_info.get("committer", {}).get("date")
                    or commit_info.get("author", {}).get("date")
                )
                return sha, committer_date, new_etag, False
    except Exception:
        pass
    return None, None, known_etag, False


def get_google_models_registry(force_update: bool = False) -> dict:
    global _registry_mem_cache, _registry_file_mtime, _registry_last_checked_ts

    cache_file = settings.app_dir / "google_ai_studio.json"
    meta_file = settings.app_dir / "google_ai_studio.meta.json"
    local_data: dict | None = _registry_mem_cache

    if cache_file.exists():
        try:
            current_mtime = cache_file.stat().st_mtime
            if local_data is None or current_mtime != _registry_file_mtime:
                with open(cache_file, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                _registry_mem_cache = local_data
                _registry_file_mtime = current_mtime
        except Exception:
            local_data = _registry_mem_cache

    now_mono = time.monotonic()
    ttl_expired = (
        _registry_last_checked_ts == 0.0
        or (now_mono - _registry_last_checked_ts) >= REGISTRY_CHECK_TTL_SECONDS
    )

    if local_data is not None and not force_update and not ttl_expired:
        return local_data

    meta = _load_registry_meta(meta_file)
    known_sha = meta.get("commit_sha")
    known_etag = meta.get("etag")

    latest_sha, remote_commit_date, new_etag, not_modified = _check_github_file_commit(
        known_etag if not force_update else None
    )

    if local_data is not None:
        local_ts = _parse_iso_timestamp(str(local_data.get("last_updated", "")))
        if not_modified or (latest_sha and latest_sha == known_sha):
            _registry_last_checked_ts = now_mono
            meta["etag"] = new_etag
            meta["checked_at"] = datetime.now(timezone.utc).isoformat()
            _save_registry_meta(meta_file, meta)
            return local_data

        remote_commit_ts = _parse_iso_timestamp(remote_commit_date)
        if local_ts > 0 and remote_commit_ts > 0 and local_ts > remote_commit_ts:
            _registry_last_checked_ts = now_mono
            if latest_sha:
                meta["commit_sha"] = latest_sha
                meta["commit_date"] = remote_commit_date
                meta["etag"] = new_etag
                meta["checked_at"] = datetime.now(timezone.utc).isoformat()
                _save_registry_meta(meta_file, meta)
            return local_data

    download_url = (
        f"https://raw.githubusercontent.com/{GITHUB_REPO}/{latest_sha}/{GITHUB_FILE_PATH}"
        if latest_sha
        else GITHUB_RAW_URL
    )

    try:
        response = httpx.get(download_url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        _registry_last_checked_ts = now_mono

        if local_data is not None:
            local_ts = _parse_iso_timestamp(str(local_data.get("last_updated", "")))
            remote_ts = _parse_iso_timestamp(str(data.get("last_updated", "")))
            if local_ts > 0 and remote_ts > 0 and local_ts > remote_ts:
                return local_data

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        _registry_mem_cache = data
        _registry_file_mtime = cache_file.stat().st_mtime
        if latest_sha:
            meta["commit_sha"] = latest_sha
            meta["commit_date"] = remote_commit_date
            meta["etag"] = new_etag
        meta["checked_at"] = datetime.now(timezone.utc).isoformat()
        _save_registry_meta(meta_file, meta)

        return data
    except (httpx.HTTPError, ValueError) as e:
        _registry_last_checked_ts = now_mono
        if local_data is not None:
            return local_data
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
            sig_b64 = p.get("thought_signature_b64")
            if sig_b64:
                google_parts.append(
                    {
                        "function_call": {
                            "name": p["name"],
                            "args": p.get("args", {}),
                        },
                        "thought_signature": base64.b64decode(sig_b64),
                    }
                )
        elif p_type == "tool_response":
            continue
        elif "function_call" in p:
            google_parts.append({"function_call": p["function_call"]})
        elif "function_response" in p:
            google_parts.append({"function_response": p["function_response"]})
        elif "inline_data" in p:
            google_parts.append({"inline_data": p["inline_data"]})
        elif "file_data" in p:
            google_parts.append({"file_data": p["file_data"]})
        elif "text" in p and p["text"] is not None:
            google_parts.append({"text": str(p["text"])})

    return google_parts or [{"text": str(fallback_content)}]


async def _build_google_attachment_parts(
    attachments: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[SourceItem]]:
    """Load local or external attachments and format them as Google GenAI parts and SourceItems."""
    if not attachments:
        return [], []

    att_entries: list[tuple[str, str]] = []
    for a in attachments:
        if isinstance(a, dict):
            aid = a.get("id") or a.get("attachment_id")
            if aid:
                att_entries.append((str(aid), str(a.get("filename") or "attachment")))
    if not att_entries:
        return [], []

    att_ids = [aid for aid, _ in att_entries]
    async with async_session_maker() as session:
        rows = (
            (
                await session.execute(
                    select(Attachment).where(Attachment.id.in_(att_ids))
                )
            )
            .scalars()
            .all()
        )
    by_id = {r.id: r for r in rows}
    storage = FileStorageManager()
    parts: list[dict[str, Any]] = []
    sources: list[SourceItem] = []

    for aid, filename in att_entries:
        att = by_id.get(aid)
        if att is None:
            continue
        sources.append(
            SourceItem(
                kind="attachment",
                title=filename,
                attachment_id=att.id,
                url=att.external_uri,
                mime_type=att.mime_type,
            )
        )
        if att.file_path and storage.path_exists(att.file_path):
            raw_bytes = await asyncio.to_thread(
                storage.resolve_path(att.file_path).read_bytes
            )
            parts.append(
                {
                    "inline_data": {
                        "mime_type": att.mime_type,
                        "data": raw_bytes,
                    }
                }
            )
        elif att.external_uri:
            parts.append(
                {
                    "file_data": {
                        "mime_type": att.mime_type,
                        "file_uri": att.external_uri,
                    }
                }
            )

    return parts, sources


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

    async def list_models(
        self, force_update: bool = False
    ) -> dict[str, Any] | list[dict[str, Any]]:
        registry = await asyncio.to_thread(
            get_google_models_registry, force_update
        )
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
        is_admin: bool = False,
        conversation_id: str | None = None,
        history_mode: HistoryMode = EcoMode(),
        search_mode: SearchMode = StandardSearchMode(),
        temperature: float = 0.7,
        enable_builtin_tools: bool = True,
        unlocked_tools: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        if not self.is_available():
            yield ErrorEvent(message="Google API key is not set.")
            return

        attachment_sources: list[SourceItem] = []
        web_queries: list[str] = []
        web_sources: list[dict[str, str]] = []
        seen_web_urls: set[str] = set()
        assistant_attachments: list[dict[str, str]] = []

        try:
            context = await self.generate_context(conversation_id, history_mode)
            enriched_messages: list[dict[str, Any]] = []
            for msg in messages:
                msg_copy = dict(msg)
                att_parts, msg_att_sources = await _build_google_attachment_parts(
                    msg_copy.get("attachments")
                )
                attachment_sources.extend(msg_att_sources)
                if att_parts:
                    base_parts = list(msg_copy.get("parts") or [])
                    if not base_parts and msg_copy.get("content"):
                        base_parts.append({"text": str(msg_copy["content"])})
                    msg_copy["parts"] = base_parts + att_parts
                enriched_messages.append(msg_copy)

            contents, final_system_prompt = self._adapt_context_for_google(
                context, enriched_messages
            )

            if isinstance(search_mode, FullSearchMode):
                final_system_prompt = (
                    f"{final_system_prompt}\n\n{FULL_SEARCH_DIRECTIVE}"
                    if final_system_prompt
                    else FULL_SEARCH_DIRECTIVE
                )

            config: dict[str, Any] = {
                "temperature": temperature,
                "automatic_function_calling": {"disable": True},
            }
            if final_system_prompt:
                config["system_instruction"] = final_system_prompt

            tools_cfg: list[dict[str, Any]] = []
            mcp_bindings: dict[str, MCPToolBinding] = {}
            image_candidates: list[DelegationModelCandidate] = []
            models_catalog = await self.list_models()
            model_entry = (
                models_catalog.get(model, {})
                if isinstance(models_catalog, dict)
                else {}
            )
            is_gemma = (
                model.lower().startswith("gemma")
                or model_entry.get("family") == "gemma"
            )
            supports_fn_calling = bool(
                model_entry.get("features", {}).get("function_calling", True)
            )
            has_server_side_tools = not isinstance(search_mode, NoSearchMode)
            has_fn_declarations = False

            if has_server_side_tools:
                tools_cfg.append({"google_search": {}})
                if not is_gemma:
                    tools_cfg.append({"url_context": {}})

            if enable_builtin_tools and supports_fn_calling:
                declarations = builtin_registry.get_google_declarations(
                    unlocked_tools, is_admin=is_admin
                )
                mcp_declarations, mcp_bindings = await discover_mcp_tools(user_id)
                declarations.extend(mcp_declarations)
                image_candidates = resolve_delegation_models(
                    task=IMAGE_GENERATION_TASK,
                    active_model=model,
                    active_provider_id=self.provider_id,
                    provider_catalogs={self.provider_id: models_catalog},
                )
                image_decl = build_generate_image_declaration(image_candidates)
                if image_decl is not None:
                    declarations.append(image_decl)
                if declarations:
                    tools_cfg.append({"function_declarations": declarations})
                    has_fn_declarations = True

            if tools_cfg:
                config["tools"] = tools_cfg
            if has_server_side_tools and has_fn_declarations:
                config["tool_config"] = {
                    "include_server_side_tool_invocations": True
                }

            full_thoughts = ""
            full_message = ""
            tool_calls_saved: list[dict[str, Any]] = []
            last_chunk = None
            input_tokens = 0
            candidates_tokens = 0
            thoughts_tokens = 0
            delegated_cost = 0.0
            tool_ctx = ToolContext(
                user_id=user_id,
                conversation_id=conversation_id,
                is_admin=is_admin,
            )

            for _round in range(MAX_TOOL_ROUNDS):
                response = await self._client.aio.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                )

                pending_builtin_calls: list[
                    tuple[str | None, str, dict[str, Any], Any]
                ] = []
                round_last_chunk = None

                async for chunk in response:
                    last_chunk = chunk
                    round_last_chunk = chunk
                    candidates = getattr(chunk, "candidates", None) or []
                    first_cand = candidates[0] if candidates else None
                    parts = (
                        getattr(first_cand.content, "parts", None)
                        if first_cand and getattr(first_cand, "content", None)
                        else None
                    )

                    grounding = (
                        getattr(first_cand, "grounding_metadata", None)
                        if first_cand
                        else None
                    )
                    if grounding is not None:
                        c_queries, c_sources = extract_grounding_sources(grounding)
                        for q in c_queries:
                            if q not in web_queries:
                                web_queries.append(q)
                        for src in c_sources:
                            if src["url"] not in seen_web_urls:
                                seen_web_urls.add(src["url"])
                                web_sources.append(src)

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
                                thought_sig = getattr(
                                    part, "thought_signature", None
                                )
                                sig_b64: str | None = None
                                if isinstance(thought_sig, bytes):
                                    sig_b64 = base64.b64encode(thought_sig).decode(
                                        "ascii"
                                    )
                                elif isinstance(thought_sig, str):
                                    sig_b64 = thought_sig

                                saved_call: dict[str, Any] = {
                                    "type": "tool_call",
                                    "id": call_id,
                                    "name": call_name,
                                    "args": call_args,
                                }
                                if sig_b64:
                                    saved_call["thought_signature_b64"] = sig_b64
                                tool_calls_saved.append(saved_call)

                                yield ToolCallEvent(
                                    id=call_id, name=call_name, args=call_args
                                )
                                if enable_builtin_tools and (
                                    builtin_registry.get(call_name) is not None
                                    or call_name in mcp_bindings
                                    or (
                                        call_name == GENERATE_IMAGE_TOOL_NAME
                                        and bool(image_candidates)
                                    )
                                ):
                                    pending_builtin_calls.append(
                                        (
                                            call_id,
                                            call_name,
                                            call_args,
                                            thought_sig,
                                        )
                                    )
                            elif part_text:
                                full_message += part_text
                                yield TextEvent(delta=part_text)
                    elif getattr(chunk, "text", None):
                        full_message += chunk.text
                        yield TextEvent(delta=chunk.text)

                round_usage = (
                    getattr(round_last_chunk, "usage_metadata", None)
                    if round_last_chunk
                    else None
                )
                if round_usage:
                    input_tokens += round_usage.prompt_token_count or 0
                    candidates_tokens += round_usage.candidates_token_count or 0
                    thoughts_tokens += round_usage.thoughts_token_count or 0

                if not pending_builtin_calls:
                    break

                model_call_parts: list[dict[str, Any]] = []
                tool_response_parts: list[dict[str, Any]] = []

                for (
                    call_id,
                    call_name,
                    call_args,
                    thought_sig,
                ) in pending_builtin_calls:
                    call_part: dict[str, Any] = {
                        "function_call": {"name": call_name, "args": call_args}
                    }
                    if thought_sig is not None:
                        call_part["thought_signature"] = thought_sig
                    model_call_parts.append(call_part)
                    if call_name == GENERATE_IMAGE_TOOL_NAME and image_candidates:
                        exec_res = ToolExecutionResult(
                            output={"error": "Image generation returned no result."}
                        )
                        async for item in stream_google_delegated_image(
                            client=self._client,
                            candidates=image_candidates,
                            args=call_args,
                            ctx=tool_ctx,
                            step_delay_seconds=0.28,
                        ):
                            if isinstance(item, ImageProgressEvent):
                                yield item
                            else:
                                exec_res = item
                        del_usage = exec_res.output.get("usage")
                        del_model = exec_res.output.get("delegated_model")
                        if isinstance(del_usage, dict) and isinstance(del_model, str):
                            d_in = int(del_usage.get("input_tokens") or 0)
                            d_out = int(del_usage.get("output_tokens") or 0) + int(
                                del_usage.get("thoughts_tokens") or 0
                            )
                            delegated_cost += await self.calcul_price(
                                del_model, d_in, is_input=True
                            )
                            delegated_cost += await self.calcul_price(
                                del_model, d_out, is_input=False
                            )
                    elif call_name in mcp_bindings:
                        exec_res = await execute_mcp_tool(
                            mcp_bindings[call_name], call_args, tool_ctx
                        )
                    else:
                        exec_res = await builtin_registry.execute(
                            call_name, call_args, tool_ctx
                        )
                    tool_calls_saved.append(
                        {
                            "type": "tool_response",
                            "id": call_id,
                            "name": call_name,
                            "result": exec_res.output,
                        }
                    )
                    yield ToolResultEvent(
                        id=call_id, name=call_name, result=exec_res.output
                    )

                    for att_info in exec_res.attachments:
                        stream_offset = len(full_message)
                        assistant_attachments.append(
                            {
                                "id": att_info.id,
                                "filename": att_info.filename,
                                "mime_type": att_info.mime_type,
                                "insert_offset": stream_offset,
                            }
                        )
                        yield AttachmentEvent(
                            id=att_info.id,
                            filename=att_info.filename,
                            mime_type=att_info.mime_type,
                            is_generated=att_info.is_generated,
                            external_uri=att_info.external_uri,
                            insert_offset=stream_offset,
                        )

                    tool_response_parts.append(
                        {
                            "function_response": {
                                "name": call_name,
                                "response": exec_res.output,
                            }
                        }
                    )

                contents.append({"role": "model", "parts": model_call_parts})
                contents.append({"role": "user", "parts": tool_response_parts})

        except Exception as exc:  # noqa: BLE001
            yield ErrorEvent(message=str(exc))
            return

        if web_sources and not isinstance(search_mode, NoSearchMode):
            max_images = 2 if isinstance(search_mode, FullSearchMode) else 1
            candidate_web_sources = web_sources[:3]
            tasks = [
                fetch_and_store_web_image(
                    src["url"],
                    user_id=user_id,
                    title=src["title"],
                    source_page_url=src["url"],
                )
                for src in candidate_web_sources
            ]
            fetched_atts = await asyncio.gather(*tasks)
            kept = 0
            for src, att in zip(candidate_web_sources, fetched_atts):
                if att is not None:
                    kept += 1
                    ext = (
                        att.mime_type.split("/", 1)[-1].split("+", 1)[0]
                        if "/" in att.mime_type
                        else "png"
                    )
                    fname = f"web_image_{kept}.{ext}"
                    offset = find_grounding_insert_offset(
                        full_message, src, slot_index=kept - 1
                    )
                    assistant_attachments.append(
                        {
                            "id": att.id,
                            "filename": fname,
                            "mime_type": att.mime_type,
                            "insert_offset": offset,
                            "label": src.get("title") or fname,
                        }
                    )
                    yield AttachmentEvent(
                        id=att.id,
                        filename=fname,
                        mime_type=att.mime_type,
                        is_generated=False,
                        external_uri=att.external_uri,
                        insert_offset=offset,
                    )
                    if kept >= max_images:
                        break

        source_items: list[SourceItem] = list(attachment_sources)
        for src in web_sources:
            source_items.append(
                SourceItem(
                    kind="web",
                    title=src["title"],
                    url=src["url"],
                    queries=web_queries,
                )
            )
        if source_items:
            yield SourcesEvent(items=source_items)

        resolved_model = (
            getattr(last_chunk, "model_version", None) or model
            if last_chunk is not None
            else model
        )
        total_output_tokens = candidates_tokens + thoughts_tokens

        pricing_model = resolved_model
        if isinstance(models_catalog, dict) and pricing_model not in models_catalog:
            pricing_model = model

        input_cost = await self.calcul_price(pricing_model, input_tokens, is_input=True)
        output_cost = (
            await self.calcul_price(
                pricing_model, total_output_tokens, is_input=False
            )
            + delegated_cost
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
                attachments=user_msg.get("attachments"),
            )

            persisted_message = full_message
            unreferenced_atts = [
                a
                for a in assistant_attachments
                if f"attachment://{a['id']}" not in persisted_message
            ]
            # Sort descending by offset so splicing earlier attachments does not shift later offsets
            for att_entry in sorted(
                unreferenced_atts,
                key=lambda x: int(x.get("insert_offset") or 0),
                reverse=True,
            ):
                aid = att_entry["id"]
                label = str(att_entry.get("label") or att_entry.get("filename") or "attachment")
                is_img = str(att_entry.get("mime_type") or "").startswith("image/")
                tag = (
                    f"![{label}](attachment://{aid})"
                    if is_img
                    else f"[{label}](attachment://{aid})"
                )
                raw_off = int(att_entry.get("insert_offset") or 0)
                if raw_off <= 0 and persisted_message:
                    first_break = persisted_message.find("\n\n")
                    raw_off = (
                        first_break
                        if first_break != -1
                        else len(persisted_message)
                    )
                off = max(0, min(raw_off, len(persisted_message)))
                before = persisted_message[:off].rstrip()
                after = persisted_message[off:].lstrip()
                if before and after:
                    persisted_message = f"{before}\n\n{tag}\n\n{after}"
                elif before:
                    persisted_message = f"{before}\n\n{tag}"
                elif after:
                    persisted_message = f"{tag}\n\n{after}"
                else:
                    persisted_message = tag

            assistant_parts: list[dict[str, Any]] = []
            if full_thoughts:
                assistant_parts.append({"type": "thinking", "text": full_thoughts})
            assistant_parts.extend(tool_calls_saved)
            if source_items:
                assistant_parts.append(
                    {
                        "type": "sources",
                        "items": [
                            s.model_dump(exclude_none=True) for s in source_items
                        ],
                    }
                )
            assistant_parts.append({"type": "text", "text": persisted_message})

            _, assistant_msg_id = await save_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                model=resolved_model,
                content=persisted_message,
                parts=assistant_parts,
                token_count=total_output_tokens,
                cost=output_cost,
                attachments=assistant_attachments or None,
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
