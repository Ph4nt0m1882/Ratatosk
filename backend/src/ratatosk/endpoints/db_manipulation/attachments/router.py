from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from ratatosk.core.idle_worker import idle_worker
from ratatosk.core.security import get_current_admin, get_current_user
from ratatosk.db.models import User

from .get import get_attachment_full, get_attachment_preview
from .models import AttachmentStatsResponse, AttachmentUploadResponse
from .remove import (
    ATTACHMENT_PURGE_TASK,
    delete_attachment,
    purge_expired_attachments,
)
from .stats import ATTACHMENT_STATS_TASK, collect_attachment_stats, get_attachment_stats
from .uploads import upload_attachment

idle_worker.register(
    ATTACHMENT_PURGE_TASK,
    purge_expired_attachments,
    min_interval=30.0,
    max_interval=1800.0,
    dirty_only=True,
    initial_dirty=True,
)
idle_worker.register(
    ATTACHMENT_STATS_TASK,
    collect_attachment_stats,
    min_interval=30.0,
    max_interval=3600.0,
    dirty_only=True,
    initial_dirty=True,
)

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.post("/upload")
async def upload_attachment_endpoint(
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
) -> AttachmentUploadResponse:
    return await upload_attachment(file, user)


@router.get("/preview")
async def get_attachment_preview_endpoint(
    attachment_id: str, user: Annotated[User, Depends(get_current_user)]
) -> Response:
    return await get_attachment_preview(attachment_id, user)


@router.get("/full")
async def get_attachment_full_endpoint(
    attachment_id: str,
    user: Annotated[User, Depends(get_current_user)],
    filename: str | None = None,
    download: bool = False,
) -> Response:
    return await get_attachment_full(attachment_id, user, filename, download)


@router.get("/stats", dependencies=[Depends(get_current_admin)])
async def get_attachment_stats_endpoint(
    refresh: bool = False,
) -> AttachmentStatsResponse:
    return await get_attachment_stats(refresh=refresh)


@router.delete("")
async def delete_attachment_endpoint(
    attachment_id: str,
    user: Annotated[User, Depends(get_current_user)],
    strict: bool = False,
) -> dict[str, str | int]:
    return await delete_attachment(attachment_id, user, strict=strict)


@router.post("/purge", dependencies=[Depends(get_current_admin)])
async def purge_attachments_endpoint() -> dict[str, int]:
    purged = await idle_worker.run_task_now(ATTACHMENT_PURGE_TASK)
    return {"purged": int(purged)}
