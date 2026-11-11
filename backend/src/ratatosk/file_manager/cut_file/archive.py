import tarfile
import zipfile
from pathlib import Path
from typing import Any


def inspect_archive_tree(archive_path: Path, max_entries: int = 200) -> dict[str, Any]:
    """List archive entries without extracting payloads (supports .zip and .tar*)."""
    entries: list[dict[str, Any]] = []
    truncated = False

    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            infos = zf.infolist()
            total_entries = len(infos)
            if total_entries > max_entries:
                truncated = True
                infos = infos[:max_entries]

            for info in infos:
                entries.append(
                    {
                        "path": info.filename,
                        "is_dir": info.is_dir(),
                        "size": info.file_size,
                        "compressed_size": info.compress_size,
                    }
                )
        return {
            "format": "zip",
            "total_entries": total_entries,
            "truncated": truncated,
            "entries": entries,
        }

    # Fallback to tar (.tar, .tar.gz, .tar.bz2, .tar.xz) via bounded sequential scan
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            count = 0
            while (member := tf.next()) is not None:
                count += 1
                if count > max_entries:
                    truncated = True
                    break
                entries.append(
                    {
                        "path": member.name,
                        "is_dir": member.isdir(),
                        "size": member.size,
                    }
                )
        return {
            "format": "tar",
            "total_entries": len(entries) if not truncated else None,
            "truncated": truncated,
            "entries": entries,
        }
    except tarfile.TarError as exc:
        raise ValueError(f"Unsupported or corrupted archive: {archive_path}") from exc

