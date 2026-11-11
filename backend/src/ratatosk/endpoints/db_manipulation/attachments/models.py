from datetime import datetime

from pydantic import BaseModel


class AttachmentUploadResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    size: int
    width: int | None = None
    height: int | None = None
    created_at: datetime


class SourceAttachmentStats(BaseModel):
    source: str
    total_count: int
    local_files_count: int
    unique_local_files_count: int
    external_refs_count: int
    expired_count: int
    logical_bytes: int
    unique_disk_bytes: int
    avg_local_file_bytes: int


class DiskBucketStats(BaseModel):
    files_count: int = 0
    bytes: int = 0


class AttachmentDiskStats(BaseModel):
    uploads: DiskBucketStats
    generated: DiskBucketStats
    tools: DiskBucketStats
    previews: DiskBucketStats
    tools_breakdown: dict[str, DiskBucketStats]
    total_bytes: int
    orphan_files_count: int


class AttachmentTotalsStats(BaseModel):
    total_count: int
    local_files_count: int
    unique_local_files_count: int
    external_refs_count: int
    expired_count: int
    logical_bytes: int


class AttachmentStatsResponse(BaseModel):
    updated_at: datetime
    totals: AttachmentTotalsStats
    by_source: list[SourceAttachmentStats]
    disk: AttachmentDiskStats
