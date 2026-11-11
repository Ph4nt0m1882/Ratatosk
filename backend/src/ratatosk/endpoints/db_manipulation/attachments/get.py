import asyncio
import mimetypes
import os
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import cv2
import orjson
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from PIL import Image

from ratatosk.db.models import Attachment, User
from ratatosk.db.session import async_session_maker
from ratatosk.file_manager import FileStorageManager
from ratatosk.file_manager.cut_file import (
    extract_video_thumbnail_webp,
    inspect_archive_tree,
    prepare_image_for_preview,
    read_smart_chunk,
)

TEXT_MIMES = frozenset(
    {
        "application/json",
        "application/ld+json",
        "application/xml",
        "application/javascript",
        "application/typescript",
        "application/yaml",
        "application/x-yaml",
        "application/toml",
        "application/x-sh",
        "application/sql",
    }
)

ARCHIVE_MIMES = frozenset(
    {
        "application/zip",
        "application/x-zip-compressed",
        "application/x-tar",
        "application/gzip",
        "application/x-gzip",
        "application/x-bzip2",
        "application/x-xz",
    }
)


async def _load_local_attachment(
    attachment_id: str, user: User, storage: FileStorageManager | None = None
) -> tuple[Attachment, Path]:
    if not isinstance(storage, FileStorageManager):
        storage = FileStorageManager()

    async with async_session_maker() as session:
        att = await session.get(Attachment, attachment_id)
        if att is None:
            raise HTTPException(status_code=404, detail="Attachment not found.")

        if att.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied.")

        if not att.file_path:
            raise HTTPException(
                status_code=400, detail="External reference has no local file."
            )

        try:
            return att, (storage.resolve_path(att.file_path))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Attachment file not found.")


async def get_attachment_full(
    attachment_id: str, user: User, filename=None, download=False
) -> FileResponse:
    att, file_path = await _load_local_attachment(attachment_id, user)
    clean_path = (
        Path(filename).name
        if filename
        else f"attachment_{att.id[:8]}{mimetypes.guess_extension(att.mime_type) or ''}"
    )

    return FileResponse(
        file_path,
        headers={
            "X-Attachment-Complete": "true",
            "X-Original-Mime-Type": att.mime_type,
            "X-Preview-Kind": "raw",
            "Cache-Control": "private, max-age=31536000, immutable",
        },
        media_type=att.mime_type,
        filename=clean_path,
        content_disposition_type="attachment" if download else "inline",
    )


def _placeholder_response(att: Attachment) -> Response:
    payload = orjson.dumps(
        {
            "type": "placeholder",
            "mime_type": att.mime_type,
            "size": att.file_size,
        }
    )
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "X-Attachment-Complete": "false",
            "X-Original-Mime-Type": att.mime_type,
            "X-Preview-Kind": "placeholder",
            "Cache-Control": "private, max-age=31536000, immutable",
        },
    )


def _get_or_build_webp_cache(
    storage: FileStorageManager,
    file_hash: str | None,
    builder: Callable[[], bytes],
) -> tuple[Path | None, bytes | None]:
    if file_hash:
        cache_path = storage.preview_cache_path(file_hash)
        if cache_path.is_file():
            return cache_path, None
        webp_bytes = builder()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_str = tempfile.mkstemp(dir=cache_path.parent, prefix=".tmp_prev_")
        tmp_path = Path(tmp_str)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(webp_bytes)
            tmp_path.replace(cache_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        return cache_path, None
    return None, builder()


async def _serve_visual_thumbnail(
    storage: FileStorageManager,
    att: Attachment,
    builder: Callable[[], bytes],
) -> Response:
    try:
        cache_path, raw_webp = await asyncio.to_thread(
            _get_or_build_webp_cache, storage, att.file_hash, builder
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        Image.DecompressionBombError,
        cv2.error,
    ):
        return _placeholder_response(att)

    headers = {
        "X-Attachment-Complete": "false",
        "X-Original-Mime-Type": att.mime_type,
        "X-Preview-Kind": "thumbnail",
        "Cache-Control": "private, max-age=31536000, immutable",
    }
    if cache_path is not None:
        return FileResponse(
            cache_path,
            media_type="image/webp",
            filename=f"preview_{att.id[:8]}.webp",
            content_disposition_type="inline",
            headers=headers,
        )
    return Response(content=raw_webp, media_type="image/webp", headers=headers)


async def get_attachment_preview(attachment_id: str, user: User) -> Response:
    storage = FileStorageManager()
    att, file_path = await _load_local_attachment(attachment_id, user, storage)
    mime = att.mime_type.split(";")[0].strip().lower()

    if mime == "image/svg+xml":
        if att.file_size <= 256 * 1024:
            return FileResponse(
                file_path,
                headers={
                    "X-Attachment-Complete": "true",
                    "X-Original-Mime-Type": att.mime_type,
                    "X-Preview-Kind": "raw",
                    "Cache-Control": "private, max-age=31536000, immutable",
                },
                media_type=att.mime_type,
                filename=f"attachment_{att.id[:8]}.svg",
                content_disposition_type="inline",
            )
        return _placeholder_response(att)

    elif mime.startswith("text/") or mime in TEXT_MIMES:
        content, is_complete = await asyncio.to_thread(
            read_smart_chunk, file_path, target_kb=64, margin_kb=8, encoding="auto"
        )
        return Response(
            content,
            headers={
                "X-Attachment-Complete": "true" if is_complete else "false",
                "X-Original-Mime-Type": att.mime_type,
                "X-Preview-Kind": "raw" if is_complete else "excerpt",
                "Cache-Control": "private, max-age=31536000, immutable",
            },
            media_type=f"{mime}; charset=utf-8",
        )

    elif mime.startswith("image/"):
        small_dims = (att.width or 0) <= 1280 and (att.height or 0) <= 1280
        if att.file_size <= 256 * 1024 and small_dims and att.width is not None:
            return FileResponse(
                file_path,
                headers={
                    "X-Attachment-Complete": "true",
                    "X-Original-Mime-Type": att.mime_type,
                    "X-Preview-Kind": "raw",
                    "Cache-Control": "private, max-age=31536000, immutable",
                },
                media_type=att.mime_type,
                filename=f"attachment_{att.id[:8]}{mimetypes.guess_extension(mime) or ''}",
                content_disposition_type="inline",
            )
        return await _serve_visual_thumbnail(
            storage,
            att,
            lambda: prepare_image_for_preview(
                file_path, max_dimension=1280, quality=80
            ),
        )

    elif mime.startswith("video/"):
        return await _serve_visual_thumbnail(
            storage,
            att,
            lambda: extract_video_thumbnail_webp(
                file_path, max_dimension=1280, quality=80
            ),
        )

    elif mime in ARCHIVE_MIMES:
        try:
            tree = await asyncio.to_thread(inspect_archive_tree, file_path)
        except (OSError, ValueError, EOFError, zipfile.BadZipFile):
            return _placeholder_response(att)
        return Response(
            content=orjson.dumps(tree),
            media_type="application/json",
            headers={
                "X-Attachment-Complete": "false",
                "X-Original-Mime-Type": att.mime_type,
                "X-Preview-Kind": "archive-tree",
                "Cache-Control": "private, max-age=31536000, immutable",
            },
        )

    else:
        return _placeholder_response(att)
