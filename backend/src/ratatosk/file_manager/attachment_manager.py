import asyncio
import hashlib
import io
import os
import re
import struct
import tempfile
from collections.abc import AsyncIterator, Iterator
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, Protocol

from ratatosk.core.config import settings


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


class DestPaths(StrEnum):
    UPLOADS = "uploads"
    GENERATED = "generated"
    TOOLS = "tools"
    PREVIEWS = "previews"


class FileStorageManager:
    def __init__(
        self,
        root_dir: Path | None = None,
        algorithm: str = "blake2b",
        digest_size: int = 32,
        chunk_size: int = 65536,
    ) -> None:
        self.root = (root_dir or settings.attachments_dir).resolve()
        self.algorithm = algorithm
        self.digest_size = digest_size
        self.chunk_size = chunk_size

        self.root.mkdir(parents=True, exist_ok=True)
        for sub in DestPaths:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def _new_hasher(self):
        if self.algorithm in ("blake2b", "blake2s"):
            return hashlib.new(self.algorithm, digest_size=self.digest_size)
        return hashlib.new(self.algorithm)

    @staticmethod
    def _sanitize_tool_name(tool_name: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9._-]+", "_", tool_name).strip("._-")
        if not clean:
            raise ValueError(f"Invalid tool_name: {tool_name!r}")
        return clean[:80]

    def _build_path(
        self,
        file_type: DestPaths,
        file_hash: str,
        tool_name: str | None = None,
    ) -> Path:
        prefix = file_hash[:2]
        base = self.root / file_type
        if file_type == DestPaths.TOOLS and tool_name:
            base = base / self._sanitize_tool_name(tool_name)
        return base / prefix / file_hash

    def _finalize_temp_file(
        self,
        temp_path: Path,
        file_type: DestPaths,
        file_hash: str,
        tool_name: str | None,
    ) -> str:
        final_path = self._build_path(file_type, file_hash, tool_name)
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
        else:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.replace(final_path)
        return final_path.relative_to(self.root).as_posix()

    def save_file(
        self,
        file_type: DestPaths,
        source: bytes | BinaryIO,
        tool_name: str | None = None,
    ) -> tuple[str, str, int]:
        """Save bytes or sync stream atomically. Returns (hash, relative_path, file_size)."""
        flux: BinaryIO = io.BytesIO(source) if isinstance(source, bytes) else source

        if hasattr(flux, "seek"):
            flux.seek(0)

        hasher = self._new_hasher()
        file_size = 0

        fd, temp_path_str = tempfile.mkstemp(dir=self.root, prefix=".tmp_")
        temp_path = Path(temp_path_str)

        try:
            with os.fdopen(fd, "wb") as f_temp:
                while chunk := flux.read(self.chunk_size):
                    hasher.update(chunk)
                    f_temp.write(chunk)
                    file_size += len(chunk)

            file_hash = hasher.hexdigest()
            rel_path = self._finalize_temp_file(
                temp_path, file_type, file_hash, tool_name
            )
            return file_hash, rel_path, file_size

        finally:
            temp_path.unlink(missing_ok=True)

    async def save_async_stream(
        self,
        file_type: DestPaths,
        source: AsyncReadable,
        tool_name: str | None = None,
    ) -> tuple[str, str, int]:
        """Save a FastAPI UploadFile (or async stream) without blocking the event loop."""
        hasher = self._new_hasher()
        file_size = 0

        fd, temp_path_str = tempfile.mkstemp(dir=self.root, prefix=".tmp_")
        temp_path = Path(temp_path_str)

        try:
            with os.fdopen(fd, "wb") as f_temp:
                while chunk := await source.read(self.chunk_size):
                    hasher.update(chunk)
                    await asyncio.to_thread(f_temp.write, chunk)
                    file_size += len(chunk)

            file_hash = hasher.hexdigest()
            rel_path = await asyncio.to_thread(
                self._finalize_temp_file, temp_path, file_type, file_hash, tool_name
            )
            return file_hash, rel_path, file_size

        finally:
            temp_path.unlink(missing_ok=True)

    def _secure_path(self, bdd_path: str | Path) -> Path:
        raw = Path(bdd_path)
        target = (raw if raw.is_absolute() else (self.root / raw)).resolve()
        if not target.is_relative_to(self.root):
            raise PermissionError(
                f"Refused access outside dedicated attachments folder: {target}"
            )
        if not target.is_file():
            raise FileNotFoundError(f"Attachment file not found on server: {target}")
        return target

    def resolve_path(self, bdd_path: str | Path) -> Path:
        """Validate and return the absolute disk Path for a stored relative path."""
        return self._secure_path(bdd_path)

    def preview_cache_path(self, file_hash: str) -> Path:
        """Return the deterministic disk path for a cached WebP preview."""
        clean_hash = re.sub(r"[^a-fA-F0-9]", "", file_hash)
        if not clean_hash:
            raise ValueError("Invalid file_hash for preview cache.")
        return self.root / DestPaths.PREVIEWS / clean_hash[:2] / f"{clean_hash}.webp"

    def read_bytes(self, bdd_path: str | Path) -> bytes:
        target = self._secure_path(bdd_path)
        return target.read_bytes()

    def read_flow(self, bdd_path: str | Path) -> Iterator[bytes]:
        target = self._secure_path(bdd_path)
        with open(target, "rb") as f:
            while chunk := f.read(self.chunk_size):
                yield chunk

    async def read_async_flow(self, bdd_path: str | Path) -> AsyncIterator[bytes]:
        target = self._secure_path(bdd_path)
        with open(target, "rb") as f:
            while chunk := await asyncio.to_thread(f.read, self.chunk_size):
                yield chunk

    def path_exists(self, bdd_path: str | Path) -> bool:
        try:
            self._secure_path(bdd_path)
            return True
        except FileNotFoundError, PermissionError:
            return False

    def hash_exists(
        self,
        file_type: DestPaths,
        file_hash: str,
        tool_name: str | None = None,
    ) -> str | None:
        path = self._build_path(file_type, file_hash, tool_name)
        return path.relative_to(self.root).as_posix() if path.is_file() else None

    def delete_file(self, bdd_path: str | Path) -> bool:
        """Delete a stored attachment file and prune its empty hash bucket directory."""
        try:
            target = self._secure_path(bdd_path)
        except FileNotFoundError:
            return False

        parent = target.parent
        target.unlink(missing_ok=True)

        # Clean up empty 2-char hash bucket directory if nothing else is inside
        try:
            if parent != self.root and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass

        # Also remove cached preview if present
        preview = self.root / DestPaths.PREVIEWS / target.name[:2] / f"{target.name}.webp"
        if preview.is_file():
            preview_parent = preview.parent
            preview.unlink(missing_ok=True)
            try:
                if preview_parent != self.root and not any(preview_parent.iterdir()):
                    preview_parent.rmdir()
            except OSError:
                pass

        return True

    def get_image_dimensions(self, bdd_path: str | Path) -> tuple[int, int] | None:
        """Extract (width, height) from PNG, GIF, WebP, or JPEG headers without decoding pixels."""
        try:
            target = self._secure_path(bdd_path)
            with open(target, "rb") as f:
                header = f.read(32)
                if len(header) < 10:
                    return None

                # PNG
                if header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
                    if len(header) >= 24:
                        w, h = struct.unpack(">II", header[16:24])
                        return (w, h) if w > 0 and h > 0 else None

                # GIF
                if header[:6] in (b"GIF87a", b"GIF89a"):
                    w, h = struct.unpack("<HH", header[6:10])
                    return (w, h) if w > 0 and h > 0 else None

                # WebP
                if header[:4] == b"RIFF" and header[8:12] == b"WEBP" and len(header) >= 30:
                    chunk = header[12:16]
                    if chunk == b"VP8X":
                        w = 1 + int.from_bytes(header[24:27], "little")
                        h = 1 + int.from_bytes(header[27:30], "little")
                        return (w, h)
                    if chunk == b"VP8 " and header[23:26] == b"\x9d\x01\x2a":
                        raw_w, raw_h = struct.unpack("<HH", header[26:30])
                        return (raw_w & 0x3FFF, raw_h & 0x3FFF)
                    if chunk == b"VP8L" and header[20] == 0x2F:
                        bits = struct.unpack("<I", header[21:25])[0]
                        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)

                # JPEG
                if header[:2] == b"\xff\xd8":
                    f.seek(2)
                    sof_markers = {
                        0xC0, 0xC1, 0xC2, 0xC3,
                        0xC5, 0xC6, 0xC7, 0xC9,
                        0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
                    }
                    while b := f.read(1):
                        if b != b"\xff":
                            continue
                        while (marker_byte := f.read(1)) == b"\xff":
                            pass
                        if not marker_byte:
                            break
                        m = marker_byte[0]
                        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
                            continue
                        seg_len_raw = f.read(2)
                        if len(seg_len_raw) < 2:
                            break
                        seg_len = struct.unpack(">H", seg_len_raw)[0]
                        if seg_len < 2:
                            break
                        if m in sof_markers:
                            sof = f.read(5)
                            if len(sof) == 5:
                                _, h, w = struct.unpack(">BHH", sof)
                                return (w, h) if w > 0 and h > 0 else None
                            break
                        f.seek(seg_len - 2, os.SEEK_CUR)
        except (OSError, ValueError, struct.error):
            return None
        return None

