import asyncio
import contextlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, case, func, select

from ratatosk.core.config import settings
from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import Attachment
from ratatosk.db.session import async_session_maker
from ratatosk.file_manager import DestPaths, FileStorageManager, read_stats, record_stats

from .models import AttachmentStatsResponse

ATTACHMENT_STATS_TASK = "attachments_stats"


async def _query_db_stats() -> dict[str, Any]:
    """Single-pass SQL aggregation of attachment counts and sizes grouped by source."""
    now = datetime.now(UTC)

    async with async_session_maker() as session:
        grouped_rows = (
            await session.execute(
                select(
                    Attachment.source,
                    func.count(Attachment.id),
                    func.coalesce(
                        func.sum(case((Attachment.file_path.is_not(None), 1), else_=0)),
                        0,
                    ),
                    func.coalesce(
                        func.sum(case((Attachment.file_path.is_(None), 1), else_=0)),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    and_(
                                        Attachment.expires_at.is_not(None),
                                        Attachment.expires_at <= now,
                                    ),
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                    func.coalesce(func.sum(Attachment.file_size), 0),
                )
                .group_by(Attachment.source)
                .order_by(Attachment.source)
            )
        ).all()

        distinct_blobs = (
            select(
                Attachment.source.label("source"),
                Attachment.file_path.label("file_path"),
                func.max(Attachment.file_size).label("blob_size"),
            )
            .where(Attachment.file_path.is_not(None))
            .group_by(Attachment.source, Attachment.file_path)
            .subquery()
        )
        unique_rows = (
            await session.execute(
                select(
                    distinct_blobs.c.source,
                    func.count(),
                    func.coalesce(func.sum(distinct_blobs.c.blob_size), 0),
                ).group_by(distinct_blobs.c.source)
            )
        ).all()

        global_unique_files = (
            await session.execute(
                select(func.count(func.distinct(Attachment.file_path))).where(
                    Attachment.file_path.is_not(None)
                )
            )
        ).scalar_one()

    unique_by_source = {
        src: (int(u_count), int(u_bytes)) for src, u_count, u_bytes in unique_rows
    }

    by_source: list[dict[str, Any]] = []
    totals = {
        "total_count": 0,
        "local_files_count": 0,
        "unique_local_files_count": int(global_unique_files or 0),
        "external_refs_count": 0,
        "expired_count": 0,
        "logical_bytes": 0,
    }

    for src, total, local_cnt, ext_cnt, exp_cnt, logical_b in grouped_rows:
        u_cnt, u_bytes = unique_by_source.get(src, (0, 0))
        avg_local = (u_bytes // u_cnt) if u_cnt > 0 else 0

        entry = {
            "source": src,
            "total_count": int(total),
            "local_files_count": int(local_cnt),
            "unique_local_files_count": u_cnt,
            "external_refs_count": int(ext_cnt),
            "expired_count": int(exp_cnt),
            "logical_bytes": int(logical_b),
            "unique_disk_bytes": u_bytes,
            "avg_local_file_bytes": avg_local,
        }
        by_source.append(entry)

        totals["total_count"] += entry["total_count"]
        totals["local_files_count"] += entry["local_files_count"]
        totals["external_refs_count"] += entry["external_refs_count"]
        totals["expired_count"] += entry["expired_count"]
        totals["logical_bytes"] += entry["logical_bytes"]

    return {"totals": totals, "by_source": by_source}


def _walk_bucket(folder: Path) -> tuple[int, int]:
    """Count regular non-temporary files and total bytes inside a directory tree."""
    if not folder.is_dir():
        return 0, 0

    files_count = 0
    total_bytes = 0
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if fname.startswith(".tmp_"):
                continue
            try:
                total_bytes += os.path.getsize(os.path.join(dirpath, fname))
                files_count += 1
            except OSError:
                continue
    return files_count, total_bytes


def _scan_disk_stats(root: Path) -> dict[str, Any]:
    """Single-pass filesystem audit across uploads, generated, tools, and previews."""
    buckets: dict[str, dict[str, int]] = {}
    for sub in DestPaths:
        cnt, size_b = _walk_bucket(root / sub)
        buckets[str(sub)] = {"files_count": cnt, "bytes": size_b}

    tools_breakdown: dict[str, dict[str, int]] = {}
    tools_dir = root / DestPaths.TOOLS
    if tools_dir.is_dir():
        with contextlib.suppress(OSError), os.scandir(tools_dir) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    cnt, size_b = _walk_bucket(Path(entry.path))
                    tools_breakdown[entry.name] = {
                        "files_count": cnt,
                        "bytes": size_b,
                    }

    total_disk_bytes = sum(b["bytes"] for b in buckets.values())
    payload_files_on_disk = (
        buckets[DestPaths.UPLOADS]["files_count"]
        + buckets[DestPaths.GENERATED]["files_count"]
        + buckets[DestPaths.TOOLS]["files_count"]
    )

    return {
        "uploads": buckets[DestPaths.UPLOADS],
        "generated": buckets[DestPaths.GENERATED],
        "tools": buckets[DestPaths.TOOLS],
        "previews": buckets[DestPaths.PREVIEWS],
        "tools_breakdown": tools_breakdown,
        "total_bytes": total_disk_bytes,
        "payload_files_on_disk": payload_files_on_disk,
    }


async def collect_attachment_stats() -> dict[str, Any]:
    """Orchestrate DB + disk passes and persist the 'attachments' section in stats.json."""
    FileStorageManager()  # Ensure base attachment subfolders exist
    db_part = await _query_db_stats()
    disk_raw = await asyncio.to_thread(_scan_disk_stats, settings.attachments_dir)

    payload_files = disk_raw.pop("payload_files_on_disk", 0)
    unique_db_files = db_part["totals"]["unique_local_files_count"]
    disk_raw["orphan_files_count"] = max(0, payload_files - unique_db_files)

    return await asyncio.to_thread(
        record_stats,
        "attachments",
        {
            "totals": db_part["totals"],
            "by_source": db_part["by_source"],
            "disk": disk_raw,
        },
    )


async def get_attachment_stats(refresh: bool = False) -> AttachmentStatsResponse:
    """Return cached attachment stats from stats.json, computing on demand if missing or requested."""
    if not refresh:
        cached = await asyncio.to_thread(read_stats, "attachments")
        if cached is not None:
            return AttachmentStatsResponse.model_validate(cached)

    fresh = await idle_worker.run_task_now(ATTACHMENT_STATS_TASK)
    return AttachmentStatsResponse.model_validate(fresh)
