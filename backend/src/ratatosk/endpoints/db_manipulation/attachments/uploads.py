import asyncio
import mimetypes
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import exists, select

from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import Attachment, MessageAttachment, User
from ratatosk.db.session import async_session_maker
from ratatosk.file_manager import DestPaths, FileStorageManager

from .models import AttachmentUploadResponse
from .stats import ATTACHMENT_STATS_TASK

DRAFT_TTL = timedelta(days=1)


async def upload_attachment(file: UploadFile, user: User) -> AttachmentUploadResponse:
    storage = FileStorageManager()

    name = Path(file.filename or "unknown").name or "unknown"
    mime = file.content_type
    if not mime or mime == "application/octet-stream":
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"

    try:
        file_hash, relative_path, size = await storage.save_async_stream(
            DestPaths.UPLOADS, file
        )
    finally:
        await file.close()

    if not size:
        await asyncio.to_thread(storage.delete_file, relative_path)
        raise HTTPException(status_code=400, detail="Empty files are not allowed.")

    width, height = (None, None)
    if mime.startswith("image/"):
        dims = await asyncio.to_thread(storage.get_image_dimensions, relative_path)
        if dims:
            width, height = dims

    async with async_session_maker() as session:
        existing = (
            await session.execute(
                select(Attachment).where(
                    Attachment.user_id == user.id,
                    Attachment.source == "upload",
                    Attachment.file_hash == file_hash,
                )
            )
        ).scalar_one_or_none()

        if existing:
            is_linked = (
                await session.execute(
                    select(
                        exists().where(MessageAttachment.attachment_id == existing.id)
                    )
                )
            ).scalar()
            existing.expires_at = None if is_linked else datetime.now(UTC) + DRAFT_TTL
            await session.commit()
            att = existing
        else:
            att = Attachment(
                user_id=user.id,
                source="upload",
                file_hash=file_hash,
                mime_type=mime,
                file_size=size,
                file_path=relative_path,
                width=width,
                height=height,
                expires_at=datetime.now(UTC) + DRAFT_TTL,
            )
            session.add(att)
            await session.commit()
            await session.refresh(att)

        idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)

        return AttachmentUploadResponse(
            id=att.id,
            filename=name,
            mime_type=att.mime_type,
            size=att.file_size,
            width=att.width,
            height=att.height,
            created_at=att.created_at,
        )
