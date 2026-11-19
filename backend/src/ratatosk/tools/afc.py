import asyncio
import mimetypes
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select

from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import Attachment
from ratatosk.db.session import async_session_maker
from ratatosk.endpoints.db_manipulation.attachments.stats import ATTACHMENT_STATS_TASK
from ratatosk.file_manager import DestPaths, FileStorageManager

WEB_SEARCH_TOOL_NAME = "web_search"
MAX_WEB_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB cap for scraped web images
MIN_WEB_IMAGE_DIMENSION = 64

_META_IMG_PATTERNS = (
    re.compile(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        re.IGNORECASE,
    ),
)

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class AFCToolRegistry:
    """Registry for Automatic Function Calling (AFC) tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, func: Callable[..., Any], *, name: str | None = None) -> Callable[..., Any]:
        tool_name = name or func.__name__
        self._tools[tool_name] = func
        return func

    def get(self, name: str) -> Callable[..., Any] | None:
        return self._tools.get(name)

    def list_callables(self, names: list[str] | None = None) -> list[Callable[..., Any]]:
        if names is None:
            return list(self._tools.values())
        return [self._tools[n] for n in names if n in self._tools]


afc_registry = AFCToolRegistry()


def afc_tool(
    func: Callable[..., Any] | None = None, *, name: str | None = None
) -> Any:
    """Decorator to register a function as an Automatic Function Calling (AFC) tool."""
    if func is not None:
        return afc_registry.register(func, name=name)

    def _decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        return afc_registry.register(f, name=name)

    return _decorator


def extract_image_from_html(html: str, base_url: str) -> str | None:
    """Extract the primary illustration URL (og:image or twitter:image) from HTML."""
    head_slice = html[:65536]
    for pattern in _META_IMG_PATTERNS:
        match = pattern.search(head_slice)
        if match:
            raw_url = match.group(1).strip()
            if raw_url:
                resolved = urljoin(base_url, raw_url)
                parsed = urlparse(resolved)
                if parsed.scheme in ("http", "https"):
                    return resolved
    return None


def _detect_image_mime(data: bytes, content_type_header: str | None, url: str) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"

    if content_type_header:
        clean_ct = content_type_header.split(";", 1)[0].strip().lower()
        if clean_ct.startswith("image/"):
            return clean_ct

    guessed, _ = mimetypes.guess_type(urlparse(url).path)
    return guessed or "application/octet-stream"


async def fetch_and_store_web_image(
    url: str,
    *,
    user_id: str | None = None,
    title: str | None = None,
    source_page_url: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> Attachment | None:
    """Download a web image (or extract og:image from an HTML page) and store it as a non-generated Attachment."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    owns_client = client is None
    http = client or httpx.AsyncClient(
        timeout=6.0,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/apng,*/*;q=0.8",
        },
    )

    try:
        resp = await http.get(url)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").split(";", 1)[0].strip().lower()

        # If the URL is an HTML page, attempt to extract its og:image / twitter:image
        if "text/html" in content_type or "application/xhtml+xml" in content_type:
            img_url = extract_image_from_html(resp.text, str(resp.url))
            if not img_url:
                return None
            source_page_url = source_page_url or url
            resp = await http.get(img_url)
            resp.raise_for_status()
            content_type = (
                (resp.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
            )
            url = img_url

        raw_bytes = resp.content
        if not raw_bytes or len(raw_bytes) > MAX_WEB_IMAGE_BYTES:
            return None

        mime_type = _detect_image_mime(raw_bytes, content_type, url)
        if not mime_type.startswith("image/"):
            return None

        storage = FileStorageManager()
        file_hash, rel_path, file_size = await asyncio.to_thread(
            storage.save_file,
            DestPaths.TOOLS,
            raw_bytes,
            tool_name=WEB_SEARCH_TOOL_NAME,
        )

        dims = await asyncio.to_thread(storage.get_image_dimensions, rel_path)
        if (
            dims is None
            or dims[0] < MIN_WEB_IMAGE_DIMENSION
            or dims[1] < MIN_WEB_IMAGE_DIMENSION
        ):
            await asyncio.to_thread(storage.delete_file, rel_path)
            return None
        width, height = dims

        source_tag = f"tool:{WEB_SEARCH_TOOL_NAME}"
        ext_uri = source_page_url or url

        async with async_session_maker() as session:
            existing = (
                await session.execute(
                    select(Attachment).where(
                        Attachment.user_id == user_id,
                        Attachment.source == source_tag,
                        Attachment.file_hash == file_hash,
                    )
                )
            ).scalar_one_or_none()

            if existing is not None:
                if title and not existing.description:
                    existing.description = title
                if ext_uri and not existing.external_uri:
                    existing.external_uri = ext_uri
                await session.commit()
                await session.refresh(existing)
                return existing

            attachment = Attachment(
                user_id=user_id,
                source=source_tag,
                file_hash=file_hash,
                mime_type=mime_type,
                file_path=rel_path,
                external_uri=ext_uri,
                file_size=file_size,
                width=width,
                height=height,
                description=title,
                is_generated=False,
                expires_at=None,
            )
            session.add(attachment)
            await session.commit()
            await session.refresh(attachment)

        idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)
        return attachment
    except (httpx.HTTPError, OSError, ValueError):
        return None
    finally:
        if owns_client:
            await http.aclose()


def extract_grounding_sources(
    grounding_metadata: Any,
) -> tuple[list[str], list[dict[str, str]]]:
    """Extract deduplicated (search_queries, web_sources) from Gemini grounding_metadata."""
    if grounding_metadata is None:
        return [], []

    raw_queries = getattr(grounding_metadata, "web_search_queries", None) or []
    queries: list[str] = []
    for q in raw_queries:
        if q and isinstance(q, str) and q not in queries:
            queries.append(q)

    raw_chunks = getattr(grounding_metadata, "grounding_chunks", None) or []
    raw_supports = getattr(grounding_metadata, "grounding_supports", None) or []
    anchor_by_chunk_idx: dict[int, str] = {}
    for sup in raw_supports:
        segment = (
            getattr(sup, "segment", None)
            if not isinstance(sup, dict)
            else sup.get("segment")
        )
        indices = (
            getattr(sup, "grounding_chunk_indices", None)
            if not isinstance(sup, dict)
            else sup.get("grounding_chunk_indices")
        ) or []
        seg_text = (
            getattr(segment, "text", None)
            if segment is not None and not isinstance(segment, dict)
            else (segment.get("text") if isinstance(segment, dict) else None)
        )
        if seg_text and isinstance(seg_text, str) and seg_text.strip():
            for c_idx in indices:
                if isinstance(c_idx, int) and c_idx not in anchor_by_chunk_idx:
                    anchor_by_chunk_idx[c_idx] = seg_text.strip()

    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for idx, chunk in enumerate(raw_chunks):
        web = getattr(chunk, "web", None)
        if web is None and isinstance(chunk, dict):
            web = chunk.get("web")
        if web is None:
            continue

        uri = (
            getattr(web, "uri", None)
            if not isinstance(web, dict)
            else web.get("uri")
        )
        title = (
            getattr(web, "title", None)
            if not isinstance(web, dict)
            else web.get("title")
        )
        if uri and uri not in seen_urls:
            seen_urls.add(uri)
            entry: dict[str, str] = {"title": title or uri, "url": uri}
            if idx in anchor_by_chunk_idx:
                entry["anchor_text"] = anchor_by_chunk_idx[idx]
            sources.append(entry)

    return queries, sources


def find_grounding_insert_offset(
    full_message: str,
    src: dict[str, Any],
    slot_index: int = 0,
) -> int:
    """Compute the inline character offset in `full_message` where a grounded web image belongs."""
    if not full_message.strip():
        return 0

    anchor_text = str(src.get("anchor_text") or "").strip()
    if anchor_text:
        pos = full_message.find(anchor_text)
        if pos != -1:
            para_end = full_message.find("\n\n", pos + len(anchor_text))
            return para_end if para_end != -1 else len(full_message)

    # Split into paragraph spans `(start, end, text)`
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for part in full_message.split("\n\n"):
        start = cursor
        end = start + len(part)
        cursor = end + 2
        stripped = part.strip()
        if stripped and stripped != "---" and not stripped.startswith("#"):
            spans.append((start, end, stripped))

    if not spans:
        return len(full_message)

    # Prefer paragraphs after the opening introduction when multiple paragraphs exist
    candidate_spans = spans[1:] if len(spans) > 1 else spans
    title_words = {
        w.lower()
        for w in re.findall(r"\w{4,}", str(src.get("title") or ""))
    }
    if title_words:
        best_span = max(
            candidate_spans,
            key=lambda sp: sum(1 for w in title_words if w in sp[2].lower()),
        )
        if sum(1 for w in title_words if w in best_span[2].lower()) > 0:
            return best_span[1]

    chosen_idx = min(slot_index, len(candidate_spans) - 1)
    return candidate_spans[chosen_idx][1]
