import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from ratatosk.app import app
from ratatosk.core.config import settings
from ratatosk.core.security import create_access_token
from ratatosk.db.models import Attachment, User
from ratatosk.db.session import async_session_maker, engine


class TestAttachmentsEndpoints(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._patcher = patch.object(settings, "app_dir", Path(self._tmp.name))
        self._patcher.start()

        self.user = User(username="__ut_attach_user__", is_active=True, is_admin=False)
        self.admin = User(username="__ut_attach_admin__", is_active=True, is_admin=True)
        async with async_session_maker() as session:
            await session.execute(
                delete(User).where(
                    User.username.in_(["__ut_attach_user__", "__ut_attach_admin__"])
                )
            )
            session.add_all([self.user, self.admin])
            await session.commit()
            await session.refresh(self.user)
            await session.refresh(self.admin)

        self.headers = {"Authorization": f"Bearer {create_access_token(self.user.id)}"}
        self.admin_headers = {
            "Authorization": f"Bearer {create_access_token(self.admin.id)}"
        }
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        user_ids = [self.user.id, self.admin.id]
        async with async_session_maker() as session:
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.execute(
                delete(Attachment).where(
                    Attachment.user_id.in_(user_ids) | Attachment.user_id.is_(None)
                )
            )
            await session.commit()
        await engine.dispose()
        self._patcher.stop()
        self._tmp.cleanup()

    async def test_01_upload_deduplicate_and_empty_rejection(self) -> None:
        # 1. Empty file -> 400
        r_empty = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        self.assertEqual(r_empty.status_code, 400)

        # 2. PNG upload -> 200 with preserved extension + extracted width/height
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + b"IHDR"
            + struct.pack(">II", 512, 256)
            + b"\x08\x06\x00\x00\x00"
        )
        r1 = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("Banner_V1.png", png_bytes, "application/octet-stream")},
        )
        self.assertEqual(r1.status_code, 200, r1.text)
        data1 = r1.json()
        self.assertEqual(data1["filename"], "Banner_V1.png")
        self.assertEqual(data1["mime_type"], "image/png")
        self.assertEqual(data1["size"], len(png_bytes))
        self.assertEqual((data1["width"], data1["height"]), (512, 256))

        # 3. Re-uploading identical bytes under lowercase name deduplicates ID, keeps new echoed filename
        r2 = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("banner_v1.png", png_bytes, "image/png")},
        )
        self.assertEqual(r2.status_code, 200)
        data2 = r2.json()
        self.assertEqual(data2["id"], data1["id"])
        self.assertEqual(data2["filename"], "banner_v1.png")

    async def test_02_get_full_and_text_previews_smart_encoding(self) -> None:
        # 1. Small cp1252 CSV (Excel French accents) -> preview normalizes to UTF-8 & complete=true
        csv_cp1252 = "Produit;Catégorie;Prix\nÉcureuil;Forêt;12,50€\n".encode("cp1252")
        up_csv = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("inventaire.csv", csv_cp1252, "text/csv")},
        )
        csv_id = up_csv.json()["id"]

        r_prev_csv = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": csv_id},
            headers=self.headers,
        )
        self.assertEqual(r_prev_csv.status_code, 200)
        self.assertEqual(r_prev_csv.headers["X-Attachment-Complete"], "true")
        self.assertIn("Écureuil", r_prev_csv.text)
        self.assertIn("12,50€", r_prev_csv.text)

        # /full returns exact original cp1252 bytes untouched
        r_full_csv = await self.client.get(
            "/db/attachments/full",
            params={
                "attachment_id": csv_id,
                "filename": "inventaire_2026.csv",
                "download": "true",
            },
            headers=self.headers,
        )
        self.assertEqual(r_full_csv.status_code, 200)
        self.assertEqual(r_full_csv.content, csv_cp1252)
        self.assertIn('attachment; filename="inventaire_2026.csv"', r_full_csv.headers["content-disposition"])

        # 2. Large (>80 KB) UTF-8 Python source -> smart cut before `def ` & complete=false
        block = "def fonction_écureuil():\n    return 'noisette 🐿️'\n\n"
        large_py = (block * 2000).encode("utf-8")
        up_py = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("script.py", large_py, "text/x-python")},
        )
        py_id = up_py.json()["id"]

        r_prev_py = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": py_id},
            headers=self.headers,
        )
        self.assertEqual(r_prev_py.status_code, 200)
        self.assertEqual(r_prev_py.headers["X-Attachment-Complete"], "false")
        self.assertTrue(r_prev_py.text.endswith("return 'noisette 🐿️'"))
        self.assertLess(len(r_prev_py.content), len(large_py))

    async def test_03_image_video_archive_and_placeholder_previews(self) -> None:
        import io
        import tarfile
        import zipfile
        import cv2
        import numpy as np
        from PIL import Image

        # 1. High-res image (>1280px) -> resized WebP thumbnail cached on disk
        img_buf = io.BytesIO()
        Image.new("RGBA", (2000, 1500), (40, 120, 220, 200)).save(img_buf, format="PNG")
        up_img = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("wallpaper.png", img_buf.getvalue(), "image/png")},
        )
        img_id = up_img.json()["id"]

        r_prev_img = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": img_id},
            headers=self.headers,
        )
        self.assertEqual(r_prev_img.status_code, 200)
        self.assertEqual(r_prev_img.headers["X-Preview-Kind"], "thumbnail")
        self.assertEqual(r_prev_img.headers["X-Attachment-Complete"], "false")
        self.assertEqual(r_prev_img.headers["content-type"], "image/webp")
        with Image.open(io.BytesIO(r_prev_img.content)) as thumb:
            self.assertLessEqual(max(thumb.size), 1280)

        # 2. Synthetic video -> OpenCV WebP frame thumbnail
        vid_tmp = Path(self._tmp.name) / "sample.avi"
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(str(vid_tmp), fourcc, 10.0, (640, 360))
        for i in range(15):
            frame = np.full((360, 640, 3), fill_value=min(255, i * 15), dtype=np.uint8)
            writer.write(frame)
        writer.release()

        up_vid = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("clip.avi", vid_tmp.read_bytes(), "video/x-msvideo")},
        )
        vid_id = up_vid.json()["id"]

        r_prev_vid = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": vid_id},
            headers=self.headers,
        )
        self.assertEqual(r_prev_vid.status_code, 200)
        self.assertEqual(r_prev_vid.headers["X-Preview-Kind"], "thumbnail")
        self.assertEqual(r_prev_vid.headers["content-type"], "image/webp")
        with Image.open(io.BytesIO(r_prev_vid.content)) as vthumb:
            self.assertEqual(vthumb.size, (640, 360))

        # 3. .zip and .tar.gz archives -> JSON file tree listing
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("src/main.py", "print('hi')")
            zf.writestr("README.md", "# Hello")
        up_zip = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("project.zip", zip_buf.getvalue(), "application/zip")},
        )
        r_prev_zip = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": up_zip.json()["id"]},
            headers=self.headers,
        )
        self.assertEqual(r_prev_zip.status_code, 200)
        self.assertEqual(r_prev_zip.headers["X-Preview-Kind"], "archive-tree")
        zip_tree = r_prev_zip.json()
        self.assertEqual(zip_tree["format"], "zip")
        self.assertEqual(zip_tree["total_entries"], 2)

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tf:
            payload = b"hello tar"
            ti = tarfile.TarInfo(name="docs/guide.txt")
            ti.size = len(payload)
            tf.addfile(ti, io.BytesIO(payload))
        up_tar = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("docs.tar.gz", tar_buf.getvalue(), "application/gzip")},
        )
        r_prev_tar = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": up_tar.json()["id"]},
            headers=self.headers,
        )
        self.assertEqual(r_prev_tar.status_code, 200)
        self.assertEqual(r_prev_tar.headers["X-Preview-Kind"], "archive-tree")
        self.assertEqual(r_prev_tar.json()["entries"][0]["path"], "docs/guide.txt")

        # 4. .exe binary -> lightweight JSON placeholder (no raw bytes leaked)
        up_exe = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("installer.exe", b"MZ\x90\x00binarypayload", "application/x-msdownload")},
        )
        r_prev_exe = await self.client.get(
            "/db/attachments/preview",
            params={"attachment_id": up_exe.json()["id"]},
            headers=self.headers,
        )
        self.assertEqual(r_prev_exe.status_code, 200)
        self.assertEqual(r_prev_exe.headers["X-Preview-Kind"], "placeholder")
        self.assertEqual(r_prev_exe.headers["X-Attachment-Complete"], "false")
        self.assertEqual(r_prev_exe.json()["mime_type"], "application/x-msdownload")

    async def test_04_admin_attachment_stats_cached_and_refresh(self) -> None:
        from ratatosk.file_manager import DestPaths, FileStorageManager

        # Regular user -> 403
        r_403 = await self.client.get("/db/attachments/stats", headers=self.headers)
        self.assertEqual(r_403.status_code, 403)

        storage = FileStorageManager()
        tool_hash, tool_rel, tool_size = storage.save_file(
            DestPaths.TOOLS, b"heavy_exported_sheet" * 500, tool_name="google_workspace"
        )

        # Insert 1 heavy local tool file + 4 zero-byte external references for google_workspace
        async with async_session_maker() as session:
            session.add(
                Attachment(
                    user_id=self.user.id,
                    source="tool:google_workspace",
                    file_hash=tool_hash,
                    mime_type="application/pdf",
                    file_path=tool_rel,
                    file_size=tool_size,
                )
            )
            for idx in range(4):
                session.add(
                    Attachment(
                        user_id=self.user.id,
                        source="tool:google_workspace",
                        mime_type="application/vnd.google-apps.document",
                        external_uri=f"https://docs.google.com/document/d/doc_{idx}",
                        file_size=0,
                    )
                )
            await session.commit()

        # First call computes & caches stats.json
        r_stats = await self.client.get(
            "/db/attachments/stats", headers=self.admin_headers
        )
        self.assertEqual(r_stats.status_code, 200, r_stats.text)
        body = r_stats.json()

        gw = next(
            s for s in body["by_source"] if s["source"] == "tool:google_workspace"
        )
        self.assertEqual(gw["total_count"], 5)
        self.assertEqual(gw["local_files_count"], 1)
        self.assertEqual(gw["external_refs_count"], 4)
        # Avg local file bytes reflects the 1 local file, NOT diluted by the 4 external refs!
        self.assertEqual(gw["avg_local_file_bytes"], tool_size)
        self.assertEqual(
            body["disk"]["tools_breakdown"]["google_workspace"]["bytes"], tool_size
        )

        # Upload a new file -> cached endpoint still returns fast snapshot until refresh=true
        ts_before = body["updated_at"]
        await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("note.txt", b"hello stats", "text/plain")},
        )
        r_cached = await self.client.get(
            "/db/attachments/stats", headers=self.admin_headers
        )
        self.assertEqual(r_cached.json()["updated_at"], ts_before)

        r_refreshed = await self.client.get(
            "/db/attachments/stats",
            params={"refresh": "true"},
            headers=self.admin_headers,
        )
        self.assertNotEqual(r_refreshed.json()["updated_at"], ts_before)
        self.assertGreaterEqual(r_refreshed.json()["totals"]["total_count"], 6)

    async def test_05_delete_and_purge_preserves_shared_blob_until_last_owner(
        self,
    ) -> None:
        shared_payload = b"shared contract content across two users"

        # User 1 and Admin both upload the exact same bytes (2 DB rows, 1 disk blob)
        up1 = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("user1_doc.txt", shared_payload, "text/plain")},
        )
        up2 = await self.client.post(
            "/db/attachments/upload",
            headers=self.admin_headers,
            files={"file": ("admin_doc.txt", shared_payload, "text/plain")},
        )
        id1 = up1.json()["id"]
        id2 = up2.json()["id"]
        self.assertNotEqual(id1, id2)

        # User 1 cannot delete Admin's attachment -> 403
        r_403 = await self.client.delete(
            "/db/attachments",
            params={"attachment_id": id2},
            headers=self.headers,
        )
        self.assertEqual(r_403.status_code, 403)

        # User 1 soft-deletes their own attachment -> 200
        r_del1 = await self.client.delete(
            "/db/attachments",
            params={"attachment_id": id1},
            headers=self.headers,
        )
        self.assertEqual(r_del1.status_code, 200)

        # Purge runs -> removes id1 from DB, but keeps physical file on disk because id2 still uses it!
        r_purge1 = await self.client.post(
            "/db/attachments/purge", headers=self.admin_headers
        )
        self.assertEqual(r_purge1.status_code, 200)
        self.assertGreaterEqual(r_purge1.json()["purged"], 1)

        r_gone1 = await self.client.get(
            "/db/attachments/full",
            params={"attachment_id": id1},
            headers=self.headers,
        )
        self.assertEqual(r_gone1.status_code, 404)

        r_alive2 = await self.client.get(
            "/db/attachments/full",
            params={"attachment_id": id2},
            headers=self.admin_headers,
        )
        self.assertEqual(r_alive2.status_code, 200)
        self.assertEqual(r_alive2.content, shared_payload)

        # Now Admin deletes id2 and runs purge -> physical file is finally removed from disk!
        await self.client.delete(
            "/db/attachments",
            params={"attachment_id": id2},
            headers=self.admin_headers,
        )
        r_purge2 = await self.client.post(
            "/db/attachments/purge", headers=self.admin_headers
        )
        self.assertEqual(r_purge2.json()["purged"], 1)

        r_gone2 = await self.client.get(
            "/db/attachments/full",
            params={"attachment_id": id2},
            headers=self.admin_headers,
        )
        self.assertEqual(r_gone2.status_code, 404)

    async def test_06_strict_delete_expires_all_shared_copies(self) -> None:
        shared_payload = b"strict delete payload shared between users"

        up1 = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("u1.txt", shared_payload, "text/plain")},
        )
        up2 = await self.client.post(
            "/db/attachments/upload",
            headers=self.admin_headers,
            files={"file": ("u2.txt", shared_payload, "text/plain")},
        )
        id1 = up1.json()["id"]
        id2 = up2.json()["id"]

        # Regular user cannot use strict=True even on their own attachment -> 403
        r_403 = await self.client.delete(
            "/db/attachments",
            params={"attachment_id": id1, "strict": "true"},
            headers=self.headers,
        )
        self.assertEqual(r_403.status_code, 403)

        # Admin uses strict=True on id1 -> expires both id1 and id2
        r_strict = await self.client.delete(
            "/db/attachments",
            params={"attachment_id": id1, "strict": "true"},
            headers=self.admin_headers,
        )
        self.assertEqual(r_strict.status_code, 200)
        self.assertEqual(r_strict.json()["affected"], 2)

        # A single purge removes both DB rows and the shared physical file
        r_purge = await self.client.post(
            "/db/attachments/purge", headers=self.admin_headers
        )
        self.assertEqual(r_purge.status_code, 200)
        self.assertGreaterEqual(r_purge.json()["purged"], 2)

        for aid in (id1, id2):
            r_check = await self.client.get(
                "/db/attachments/full",
                params={"attachment_id": aid},
                headers=self.admin_headers,
            )
            self.assertEqual(r_check.status_code, 404)

    async def test_07_conversation_archive_unarchive_and_delete_hooks(self) -> None:
        from ratatosk.core.dynamic_settings import DynamicSettingsUpdate, dynamic_settings
        from ratatosk.db.models import Conversation, Message, MessageAttachment

        dynamic_settings.update(
            DynamicSettingsUpdate(
                expire_attachments_on_archive=True,
                attachment_retention_days_on_archive=0,
                attachment_retention_days_on_delete=0,
                keep_generated_attachments=True,
            )
        )

        try:
            up_shared = await self.client.post(
                "/db/attachments/upload",
                headers=self.headers,
                files={"file": ("shared.txt", b"shared across convs", "text/plain")},
            )
            up_single = await self.client.post(
                "/db/attachments/upload",
                headers=self.headers,
                files={"file": ("single.txt", b"only in conv A", "text/plain")},
            )
            shared_id = up_shared.json()["id"]
            single_id = up_single.json()["id"]

            async with async_session_maker() as session:
                gen_att = Attachment(
                    user_id=self.user.id,
                    source="generated",
                    mime_type="image/png",
                    file_size=128,
                    is_generated=True,
                )
                conv_a = Conversation(user_id=self.user.id, title="Conv A")
                conv_b = Conversation(user_id=self.user.id, title="Conv B")
                session.add_all([gen_att, conv_a, conv_b])
                await session.flush()

                msg_a = Message(
                    conversation_id=conv_a.id,
                    role="user",
                    model="gemini",
                    content="Msg A",
                )
                msg_b = Message(
                    conversation_id=conv_b.id,
                    role="user",
                    model="gemini",
                    content="Msg B",
                )
                session.add_all([msg_a, msg_b])
                await session.flush()

                # Link attachments to messages and clear draft expires_at
                for aid in (shared_id, single_id):
                    att = await session.get(Attachment, aid)
                    assert att is not None
                    att.expires_at = None

                session.add_all(
                    [
                        MessageAttachment(
                            message_id=msg_a.id,
                            attachment_id=shared_id,
                            filename="shared.txt",
                        ),
                        MessageAttachment(
                            message_id=msg_a.id,
                            attachment_id=single_id,
                            filename="single.txt",
                        ),
                        MessageAttachment(
                            message_id=msg_a.id,
                            attachment_id=gen_att.id,
                            filename="gen.png",
                        ),
                        MessageAttachment(
                            message_id=msg_b.id,
                            attachment_id=shared_id,
                            filename="shared.txt",
                        ),
                    ]
                )
                await session.commit()
                conv_a_id, conv_b_id, gen_id = conv_a.id, conv_b.id, gen_att.id

            # 1. Archive Conv A -> single_id expires, shared_id (still in active Conv B) and gen_id stay None
            r_arch = await self.client.patch(
                "/db/conversations",
                params={"conversation_id": conv_a_id},
                json={"archived": True},
                headers=self.headers,
            )
            self.assertEqual(r_arch.status_code, 200)

            async with async_session_maker() as session:
                a_single = await session.get(Attachment, single_id)
                a_shared = await session.get(Attachment, shared_id)
                a_gen = await session.get(Attachment, gen_id)
                self.assertIsNotNone(a_single.expires_at)
                self.assertIsNone(a_shared.expires_at)
                self.assertIsNone(a_gen.expires_at)

            # 2. Unarchive Conv A -> single_id expires_at is restored to None
            r_unarch = await self.client.patch(
                "/db/conversations",
                params={"conversation_id": conv_a_id},
                json={"archived": False},
                headers=self.headers,
            )
            self.assertEqual(r_unarch.status_code, 200)

            async with async_session_maker() as session:
                a_single = await session.get(Attachment, single_id)
                self.assertIsNone(a_single.expires_at)

            # 3. Delete Conv A -> single_id expires, shared_id stays None while Conv B exists, gen_id stays None
            r_del_a = await self.client.delete(
                "/db/conversations",
                params={"conversation_id": conv_a_id},
                headers=self.headers,
            )
            self.assertEqual(r_del_a.status_code, 200)

            async with async_session_maker() as session:
                a_single = await session.get(Attachment, single_id)
                a_shared = await session.get(Attachment, shared_id)
                a_gen = await session.get(Attachment, gen_id)
                self.assertIsNotNone(a_single.expires_at)
                self.assertIsNone(a_shared.expires_at)
                self.assertIsNone(a_gen.expires_at)

            # 4. Archive Conv B and run purge -> both single_id and shared_id are purged, gen_id survives!
            await self.client.patch(
                "/db/conversations",
                params={"conversation_id": conv_b_id},
                json={"archived": True},
                headers=self.headers,
            )
            await self.client.post(
                "/db/attachments/purge", headers=self.admin_headers
            )

            async with async_session_maker() as session:
                self.assertIsNone(await session.get(Attachment, single_id))
                self.assertIsNone(await session.get(Attachment, shared_id))
                self.assertIsNotNone(await session.get(Attachment, gen_id))
        finally:
            dynamic_settings.reset()

    async def test_08_end_to_end_upload_message_pagination_and_zip_export(self) -> None:
        import io
        import zipfile
        from ratatosk.db.history import save_message
        from ratatosk.providers.google.provider import _build_google_attachment_parts

        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + b"IHDR"
            + struct.pack(">II", 320, 240)
            + b"\x08\x06\x00\x00\x00"
        )

        # 1. Upload draft attachment -> expires_at is initially set (24h draft)
        up = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("croquis.png", png_bytes, "image/png")},
        )
        self.assertEqual(up.status_code, 200)
        att_id = up.json()["id"]

        async with async_session_maker() as session:
            draft = await session.get(Attachment, att_id)
            self.assertIsNotNone(draft.expires_at)

        # 2. Verify Google provider part builder hydrates inline_data bytes + SourceItem
        g_parts, g_sources = await _build_google_attachment_parts(
            [{"id": att_id, "filename": "croquis.png"}]
        )
        self.assertEqual(len(g_parts), 1)
        self.assertEqual(g_parts[0]["inline_data"]["mime_type"], "image/png")
        self.assertEqual(g_parts[0]["inline_data"]["data"], png_bytes)
        self.assertEqual(len(g_sources), 1)
        self.assertEqual(g_sources[0].kind, "attachment")
        self.assertEqual(g_sources[0].attachment_id, att_id)

        # 3. Save message with the attachment -> links MessageAttachment & clears expires_at
        conv_id, msg_id = await save_message(
            user_id=self.user.id,
            conversation_id=None,
            role="user",
            model="gemini-2.5-flash",
            content="Que penses-tu de ce croquis ?",
            attachments=[{"id": att_id, "filename": "croquis.png"}],
        )

        async with async_session_maker() as session:
            linked = await session.get(Attachment, att_id)
            self.assertIsNone(linked.expires_at)

        # 4. GET /db/conversations/messages returns the attachment metadata on the message
        r_msgs = await self.client.get(
            "/db/conversations/messages",
            params={"conversation_id": conv_id},
            headers=self.headers,
        )
        self.assertEqual(r_msgs.status_code, 200)
        msgs = r_msgs.json()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["id"], msg_id)
        self.assertEqual(len(msgs[0]["attachments"]), 1)
        msg_att = msgs[0]["attachments"][0]
        self.assertEqual(msg_att["id"], att_id)
        self.assertEqual(msg_att["filename"], "croquis.png")
        self.assertEqual(msg_att["mime_type"], "image/png")
        self.assertEqual((msg_att["width"], msg_att["height"]), (320, 240))

        # 5. GET /db/conversations/export automatically switches to .zip with attachments/croquis.png
        r_exp = await self.client.get(
            "/db/conversations/export",
            params={"conversation_id": conv_id},
            headers=self.headers,
        )
        self.assertEqual(r_exp.status_code, 200)
        self.assertEqual(r_exp.headers["content-type"], "application/zip")

        with zipfile.ZipFile(io.BytesIO(r_exp.content), "r") as zf:
            names = zf.namelist()
            self.assertIn("attachments/croquis.png", names)
            self.assertEqual(zf.read("attachments/croquis.png"), png_bytes)
            md_name = next(n for n in names if n.endswith(".md"))
            md_text = zf.read(md_name).decode("utf-8")
            self.assertIn("![croquis.png](attachments/croquis.png)", md_text)


if __name__ == "__main__":
    unittest.main()
