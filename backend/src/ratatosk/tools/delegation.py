import asyncio
import base64
import io
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageFilter, UnidentifiedImageError
from sqlalchemy import select

from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import Attachment
from ratatosk.db.session import async_session_maker
from ratatosk.endpoints.db_manipulation.attachments.stats import ATTACHMENT_STATS_TASK
from ratatosk.file_manager import DestPaths, FileStorageManager
from ratatosk.providers.schemas import ImageProgressEvent
from ratatosk.tools.builtin import (
    GeneratedAttachmentInfo,
    ToolContext,
    ToolExecutionResult,
)

GENERATE_IMAGE_TOOL_NAME = "generate_image"
IMAGE_GENERATION_TASK = "text-to-image"
VALID_ASPECT_RATIOS = ("1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3")


@dataclass(slots=True)
class DelegationModelCandidate:
    """Metadata for a candidate model eligible for capability delegation."""

    id: str
    provider_id: str
    display_name: str
    tier: str
    is_recommended: bool
    description: str
    rank: int = 999


def _iter_catalog_entries(
    raw_catalog: dict[str, Any] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(raw_catalog, dict):
        return [v for v in raw_catalog.values() if isinstance(v, dict)]
    if isinstance(raw_catalog, list):
        return [v for v in raw_catalog if isinstance(v, dict)]
    return []


def _extract_model_description(entry: dict[str, Any]) -> str:
    raw_desc = entry.get("description")
    if isinstance(raw_desc, dict):
        return str(raw_desc.get("en") or raw_desc.get("fr") or "").strip()
    if isinstance(raw_desc, str):
        return raw_desc.strip()
    return ""


def _collect_task_candidates_from_catalog(
    provider_id: str,
    raw_catalog: dict[str, Any] | list[dict[str, Any]],
    task: str,
) -> list[DelegationModelCandidate]:
    entries = _iter_catalog_entries(raw_catalog)
    all_ids = {str(e.get("id", "")) for e in entries}
    candidates: list[DelegationModelCandidate] = []

    for entry in entries:
        m_id = str(entry.get("id") or "").strip()
        if not m_id:
            continue
        tasks = entry.get("tasks") or []
        if task not in tasks:
            continue
        # Skip `-preview` duplicates when the canonical non-preview model exists
        if m_id.endswith("-preview") and m_id.removesuffix("-preview") in all_ids:
            continue

        candidates.append(
            DelegationModelCandidate(
                id=m_id,
                provider_id=provider_id,
                display_name=str(entry.get("display_name") or m_id),
                tier=str(entry.get("tier") or "standard"),
                is_recommended=bool(entry.get("is_recommended", False)),
                description=_extract_model_description(entry),
                rank=int(entry.get("rank", 999)),
            )
        )
    return candidates


def resolve_delegation_models(
    *,
    task: str,
    active_model: str,
    active_provider_id: str,
    provider_catalogs: dict[str, dict[str, Any] | list[dict[str, Any]]],
    allow_cross_provider: bool = True,
    include_legacy: bool = False,
    preferred_model: str | None = None,
) -> list[DelegationModelCandidate]:
    """Resolve and rank candidate models for a missing capability task.

    Priority 1: Intra-provider models (same provider as `active_model`).
    Priority 2: Inter-provider models (other active providers, if `allow_cross_provider=True`).
    Returns an empty list if `active_model` already supports `task` natively.
    """
    active_catalog = provider_catalogs.get(active_provider_id, {})
    for entry in _iter_catalog_entries(active_catalog):
        if entry.get("id") == active_model and task in (entry.get("tasks") or []):
            return []

    # Priority 1: Intra-provider search
    candidates = _collect_task_candidates_from_catalog(
        active_provider_id, active_catalog, task
    )

    # Priority 2: Cross-provider fallback if current provider has no model for `task`
    if not candidates and allow_cross_provider:
        for prov_id, catalog in provider_catalogs.items():
            if prov_id == active_provider_id:
                continue
            candidates.extend(
                _collect_task_candidates_from_catalog(prov_id, catalog, task)
            )

    if not candidates:
        return []

    if not include_legacy:
        non_legacy = [c for c in candidates if c.tier != "legacy"]
        if non_legacy:
            candidates = non_legacy

    tier_order = {"featured": 0, "standard": 1, "legacy": 2}
    candidates.sort(
        key=lambda c: (
            0 if (preferred_model and c.id == preferred_model) else 1,
            0 if c.is_recommended else 1,
            tier_order.get(c.tier, 1),
            c.rank,
            c.id,
        )
    )
    return candidates


def build_generate_image_declaration(
    candidates: list[DelegationModelCandidate],
) -> dict[str, Any] | None:
    """Build a dynamic Google function declaration for `generate_image` with model enum & default."""
    if not candidates:
        return None

    default_candidate = candidates[0]
    enum_ids = [c.id for c in candidates]

    model_lines: list[str] = []
    for idx, cand in enumerate(candidates):
        tags: list[str] = []
        if idx == 0:
            tags.append("DEFAULT")
        if cand.is_recommended:
            tags.append("RECOMMENDED")
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        desc_part = f": {cand.description}" if cand.description else ""
        model_lines.append(
            f"- {cand.id}{tag_str} ({cand.display_name}, tier={cand.tier}){desc_part}"
        )

    models_bullet_block = "\n".join(model_lines)
    tool_description = (
        "Generate an image from a text prompt by delegating to a specialized text-to-image model. "
        "When the tool returns `attachment_id` and `embed_markdown`, place "
        "`![caption](attachment://<attachment_id>)` at the exact spot in your Markdown response "
        "where the image should appear (e.g., after an introduction or inside the relevant section).\n"
        f"Available models (ordered by recommendation):\n{models_bullet_block}"
    )
    model_param_description = (
        f"Target text-to-image model ID. Defaults to '{default_candidate.id}' "
        f"({default_candidate.display_name}). Choose another model from the enum only when the "
        "user or task specifically requires its characteristics (e.g., Pro tier for complex "
        "artistic composition or integrated typography)."
    )

    return {
        "name": GENERATE_IMAGE_TOOL_NAME,
        "description": tool_description,
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed visual description of the image to generate "
                        "(subject, style, lighting, composition)."
                    ),
                },
                "model": {
                    "type": "string",
                    "enum": enum_ids,
                    "default": default_candidate.id,
                    "description": model_param_description,
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": list(VALID_ASPECT_RATIOS),
                    "default": "1:1",
                    "description": "Aspect ratio of the generated image.",
                },
            },
            "required": ["prompt"],
        },
    }


def build_progressive_denoising_previews(
    image_bytes: bytes,
    steps: int = 3,
) -> list[tuple[int, float, str, str]]:
    """Create progressive denoising preview frames `(step, progress, base64_data, mime_type)`.

    Simulates latent diffusion denoising stages (coarse low-frequency composition ->
    mid-frequency structure -> near-final sharpness) when a provider returns a single image frame.
    """
    if steps <= 0:
        return []

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            rgb = img.convert("RGB")
            orig_w, orig_h = rgb.size
            stage_configs = [
                (8, 10.0, 0.35),
                (3, 4.0, 0.65),
                (1, 1.2, 0.90),
            ][:steps]
            previews: list[tuple[int, float, str, str]] = []
            for idx, (downscale, blur_radius, progress) in enumerate(
                stage_configs, start=1
            ):
                small_w = max(1, orig_w // downscale)
                small_h = max(1, orig_h // downscale)
                stage_img = rgb.resize((small_w, small_h), Image.Resampling.BILINEAR)
                if downscale > 1:
                    stage_img = stage_img.resize(
                        (orig_w, orig_h), Image.Resampling.BILINEAR
                    )
                stage_img = stage_img.filter(
                    ImageFilter.GaussianBlur(radius=blur_radius)
                )
                buf = io.BytesIO()
                stage_img.save(buf, format="JPEG", quality=70)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                previews.append((idx, progress, b64, "image/jpeg"))
            return previews
    except (UnidentifiedImageError, OSError, ValueError):
        b64_raw = base64.b64encode(image_bytes).decode("ascii")
        return [
            (
                idx,
                round(idx / (steps + 1), 2),
                b64_raw,
                "image/png",
            )
            for idx in range(1, steps + 1)
        ]


async def stream_google_delegated_image(
    *,
    client: Any,
    candidates: list[DelegationModelCandidate],
    args: dict[str, Any] | None,
    ctx: ToolContext,
    denoising_steps: int = 3,
    step_delay_seconds: float = 0.02,
) -> AsyncIterator[ImageProgressEvent | ToolExecutionResult]:
    """Stream delegated image generation on Google GenAI, yielding `ImageProgressEvent`s and final `ToolExecutionResult`."""
    call_args = dict(args or {})
    prompt = str(call_args.get("prompt") or "").strip()
    if not prompt:
        yield ToolExecutionResult(
            output={"error": "Missing required 'prompt' for generate_image."}
        )
        return

    valid_ids = {c.id for c in candidates}
    requested_model = str(call_args.get("model") or "").strip()
    target_model = (
        requested_model
        if requested_model in valid_ids
        else (candidates[0].id if candidates else "gemini-3.1-flash-image")
    )

    requested_ratio = str(call_args.get("aspect_ratio") or "1:1").strip()
    aspect_ratio = (
        requested_ratio if requested_ratio in VALID_ASPECT_RATIOS else "1:1"
    )

    total_steps = max(1, denoising_steps) + 1
    yield ImageProgressEvent(
        step=0,
        total_steps=total_steps,
        progress=0.1,
        model=target_model,
        status=f"Delegating image generation to {target_model}...",
    )

    gen_config: dict[str, Any] = {
        "response_modalities": ["IMAGE"],
        "image_config": {"aspect_ratio": aspect_ratio},
    }

    collected_frames: list[tuple[bytes, str]] = []
    input_tokens = 0
    output_tokens = 0
    thoughts_tokens = 0

    try:
        response_stream = await client.aio.models.generate_content_stream(
            model=target_model,
            contents=prompt,
            config=gen_config,
        )
        native_step = 0
        async for chunk in response_stream:
            usage = getattr(chunk, "usage_metadata", None)
            if usage is not None:
                input_tokens = usage.prompt_token_count or input_tokens
                output_tokens = usage.candidates_token_count or output_tokens
                thoughts_tokens = usage.thoughts_token_count or thoughts_tokens

            cands = getattr(chunk, "candidates", None) or []
            first_cand = cands[0] if cands else None
            parts = (
                getattr(first_cand.content, "parts", None)
                if first_cand and getattr(first_cand, "content", None)
                else None
            )
            if not parts:
                continue

            for part in parts:
                is_thought = getattr(part, "thought", False) is True
                part_text = getattr(part, "text", None)
                inline = getattr(part, "inline_data", None)

                if is_thought and part_text:
                    yield ImageProgressEvent(
                        step=min(native_step, total_steps - 1),
                        total_steps=total_steps,
                        progress=0.2,
                        model=target_model,
                        status=str(part_text).strip()[:120],
                    )
                elif inline is not None and getattr(inline, "data", None):
                    raw_data = inline.data
                    if isinstance(raw_data, str):
                        raw_bytes = base64.b64decode(raw_data)
                    else:
                        raw_bytes = bytes(raw_data)
                    mime = str(getattr(inline, "mime_type", None) or "image/png")
                    collected_frames.append((raw_bytes, mime))

                    # If the stream emits intermediate image frames before the final one, forward them
                    if len(collected_frames) > 1:
                        prev_bytes, prev_mime = collected_frames[-2]
                        native_step += 1
                        yield ImageProgressEvent(
                            step=min(native_step, total_steps - 1),
                            total_steps=total_steps,
                            progress=round(
                                min(0.9, 0.2 + 0.7 * (native_step / total_steps)), 2
                            ),
                            model=target_model,
                            status=f"Streaming intermediate frame {native_step}...",
                            preview_base64=base64.b64encode(prev_bytes).decode("ascii"),
                            mime_type=prev_mime,
                        )
    except Exception as exc:  # noqa: BLE001
        yield ToolExecutionResult(
            output={
                "error": f"Delegated image generation on '{target_model}' failed: {exc}"
            }
        )
        return

    if not collected_frames:
        yield ToolExecutionResult(
            output={
                "error": f"Model '{target_model}' did not return any image data."
            }
        )
        return

    final_bytes, final_mime = collected_frames[-1]

    # When the provider returns a single image frame, emit progressive denoising steps
    if len(collected_frames) == 1 and denoising_steps > 0:
        previews = await asyncio.to_thread(
            build_progressive_denoising_previews,
            final_bytes,
            denoising_steps,
        )
        for step_idx, prog, b64_preview, prev_mime in previews:
            yield ImageProgressEvent(
                step=step_idx,
                total_steps=total_steps,
                progress=prog,
                model=target_model,
                status=f"Denoising step {step_idx}/{denoising_steps}...",
                preview_base64=b64_preview,
                mime_type=prev_mime,
            )
            if step_delay_seconds > 0:
                await asyncio.sleep(step_delay_seconds)

    storage = FileStorageManager()
    file_hash, rel_path, file_size = await asyncio.to_thread(
        storage.save_file,
        DestPaths.GENERATED,
        final_bytes,
    )
    width, height = await asyncio.to_thread(storage.get_image_dimensions, rel_path)
    source_tag = f"delegation:{target_model}"
    desc = prompt[:255]

    async with async_session_maker() as session:
        existing = (
            await session.execute(
                select(Attachment).where(
                    Attachment.user_id == ctx.user_id,
                    Attachment.source == source_tag,
                    Attachment.file_hash == file_hash,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.expires_at = None
            await session.commit()
            await session.refresh(existing)
            att = existing
        else:
            att = Attachment(
                user_id=ctx.user_id,
                source=source_tag,
                file_hash=file_hash,
                mime_type=final_mime,
                file_path=rel_path,
                file_size=file_size,
                width=width,
                height=height,
                description=desc,
                is_generated=True,
                expires_at=None,
            )
            session.add(att)
            await session.commit()
            await session.refresh(att)

    idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)
    ext = (
        final_mime.split("/", 1)[-1].split("+", 1)[0]
        if "/" in final_mime
        else "png"
    )
    filename = f"generated_{target_model.replace('/', '_')}_{att.id[:8]}.{ext}"

    yield ImageProgressEvent(
        step=total_steps,
        total_steps=total_steps,
        progress=1.0,
        model=target_model,
        status="Image generation complete.",
    )

    yield ToolExecutionResult(
        output={
            "status": "generated",
            "delegated_model": target_model,
            "aspect_ratio": aspect_ratio,
            "attachment_id": att.id,
            "filename": filename,
            "mime_type": final_mime,
            "width": width,
            "height": height,
            "embed_markdown": f"![{desc[:80]}](attachment://{att.id})",
            "placement_hint": (
                f"Insert ![caption](attachment://{att.id}) at the exact position in your "
                "Markdown response where this image should appear."
            ),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thoughts_tokens": thoughts_tokens,
            },
        },
        attachments=[
            GeneratedAttachmentInfo(
                id=att.id,
                filename=filename,
                mime_type=final_mime,
                is_generated=True,
                external_uri=None,
            )
        ],
    )
