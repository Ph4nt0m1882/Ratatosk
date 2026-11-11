import json
import os
import tempfile
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ratatosk.core.config import settings

try:
    import fcntl
except ImportError:  # Windows compatibility
    fcntl = None  # type: ignore[assignment]

_THREAD_LOCK = threading.Lock()


@contextmanager
def _stats_lock(lock_path: Path) -> Generator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _THREAD_LOCK:
        if fcntl is None:
            yield
            return

        lock_path.touch(exist_ok=True)
        with lock_path.open("r", encoding="utf-8") as fd_lock:
            fcntl.flock(fd_lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd_lock, fcntl.LOCK_UN)


def record_stats(section: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Atomically update one section inside stats.json and return the stored section."""
    stats_file = settings.stats_file
    lock_file = stats_file.with_suffix(".json.lock")

    with _stats_lock(lock_file):
        data: dict[str, Any] = {}
        if stats_file.is_file():
            try:
                loaded = json.loads(stats_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            except OSError, json.JSONDecodeError:
                data = {}

        now_iso = datetime.now(UTC).isoformat()
        sections = data.get("sections")
        if not isinstance(sections, dict):
            sections = {}
            data["sections"] = sections

        section_entry = {"updated_at": now_iso, **payload}
        sections[section] = section_entry
        data["updated_at"] = now_iso

        fd, tmp_str = tempfile.mkstemp(
            dir=stats_file.parent, prefix=".stats_", suffix=".tmp"
        )
        tmp_path = Path(tmp_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, stats_file)
        finally:
            tmp_path.unlink(missing_ok=True)

        return section_entry


def read_stats(section: str | None = None) -> dict[str, Any] | None:
    """Read the full stats.json payload or a single section if present."""
    stats_file = settings.stats_file
    if not stats_file.is_file():
        return None

    try:
        data = json.loads(stats_file.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    if section is None:
        return data

    sections = data.get("sections")
    if isinstance(sections, dict) and isinstance(sections.get(section), dict):
        return sections[section]
    return None
