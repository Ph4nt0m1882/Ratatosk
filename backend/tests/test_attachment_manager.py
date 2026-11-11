import io
import tempfile
import unittest
from pathlib import Path

from ratatosk.file_manager import DestPaths, FileStorageManager


class _FakeUploadFile:
    def __init__(self, payload: bytes) -> None:
        self._buf = io.BytesIO(payload)

    async def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)


class TestFileStorageManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mgr = FileStorageManager(root_dir=self.root, chunk_size=16)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_01_save_deduplicate_read_and_delete(self) -> None:
        payload = b"Hello Ratatosk Content-Addressed Storage!" * 10
        h1, rel1, size1 = self.mgr.save_file(DestPaths.UPLOADS, payload)
        self.assertEqual(len(h1), 64)
        self.assertEqual(size1, len(payload))
        self.assertEqual(rel1, f"uploads/{h1[:2]}/{h1}")
        self.assertTrue(self.mgr.path_exists(rel1))
        self.assertEqual(self.mgr.hash_exists(DestPaths.UPLOADS, h1), rel1)
        self.assertEqual(self.mgr.read_bytes(rel1), payload)
        self.assertEqual(b"".join(self.mgr.read_flow(rel1)), payload)

        # Deduplication: saving identical bytes again produces same hash & path
        h2, rel2, size2 = self.mgr.save_file(DestPaths.UPLOADS, io.BytesIO(payload))
        self.assertEqual((h1, rel1, size1), (h2, rel2, size2))

        # Deletion removes file AND prunes empty 2-char bucket folder
        bucket_dir = (self.root / rel1).parent
        self.assertTrue(self.mgr.delete_file(rel1))
        self.assertFalse(self.mgr.path_exists(rel1))
        self.assertFalse(bucket_dir.exists())
        self.assertFalse(self.mgr.delete_file(rel1))

    async def test_02_async_stream_and_tools_subdirectory(self) -> None:
        payload = b"Google Workspace cached spreadsheet export"
        upload = _FakeUploadFile(payload)
        h, rel, size = await self.mgr.save_async_stream(
            DestPaths.TOOLS, upload, tool_name="google_workspace"
        )
        self.assertEqual(rel, f"tools/google_workspace/{h[:2]}/{h}")
        self.assertEqual(size, len(payload))

        chunks = [c async for c in self.mgr.read_async_flow(rel)]
        self.assertEqual(b"".join(chunks), payload)

    def test_03_path_traversal_protection(self) -> None:
        with self.assertRaises(PermissionError):
            self.mgr.read_bytes("../../etc/passwd")
        self.assertFalse(self.mgr.path_exists("../../etc/passwd"))

    def test_04_extract_image_dimensions(self) -> None:
        import struct

        # Minimal PNG header (320x180)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + b"IHDR"
            + struct.pack(">II", 320, 180)
            + b"\x08\x06\x00\x00\x00"
        )
        _, png_rel, _ = self.mgr.save_file(DestPaths.UPLOADS, png_bytes)
        self.assertEqual(self.mgr.get_image_dimensions(png_rel), (320, 180))

        # Minimal GIF header (640x480)
        gif_bytes = b"GIF89a" + struct.pack("<HH", 640, 480) + b"\x00\x00\x00"
        _, gif_rel, _ = self.mgr.save_file(DestPaths.UPLOADS, gif_bytes)
        self.assertEqual(self.mgr.get_image_dimensions(gif_rel), (640, 480))

        # Minimal JPEG with APP0 + SOF0 (1024x768)
        jpeg_bytes = (
            b"\xff\xd8"
            + b"\xff\xe0" + struct.pack(">H", 6) + b"JFIF"
            + b"\xff\xc0" + struct.pack(">HBHH", 11, 8, 768, 1024) + b"\x03\x01\x11\x00"
            + b"\xff\xd9"
        )
        _, jpg_rel, _ = self.mgr.save_file(DestPaths.UPLOADS, jpeg_bytes)
        self.assertEqual(self.mgr.get_image_dimensions(jpg_rel), (1024, 768))

        # Non-image returns None
        _, txt_rel, _ = self.mgr.save_file(DestPaths.UPLOADS, b"plain text file content")
        self.assertIsNone(self.mgr.get_image_dimensions(txt_rel))

    def test_05_stats_tracker_atomic_multi_section(self) -> None:
        from unittest.mock import patch
        from ratatosk.core.config import settings
        from ratatosk.file_manager import read_stats, record_stats

        with patch.object(settings, "app_dir", self.root):
            self.assertIsNone(read_stats("attachments"))
            saved_att = record_stats("attachments", {"total_count": 12})
            self.assertEqual(saved_att["total_count"], 12)
            self.assertIn("updated_at", saved_att)

            # Writing a second section preserves the first section
            record_stats("usage", {"tokens": 4200})
            self.assertEqual(read_stats("attachments")["total_count"], 12)
            self.assertEqual(read_stats("usage")["tokens"], 4200)


if __name__ == "__main__":
    unittest.main()

