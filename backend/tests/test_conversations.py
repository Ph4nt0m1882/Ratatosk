import io
import tempfile
import unittest
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event

from ratatosk.app import app
from ratatosk.core.dynamic_settings import DynamicSettingsUpdate, dynamic_settings
from ratatosk.core.security import create_access_token
from ratatosk.db.base import Base
from ratatosk.db.history import (
    get_full_history,
    get_history_by_number,
    get_history_by_token,
    get_history_since_analysis,
    save_message,
)
from ratatosk.db.models import Conversation, Message, User
from ratatosk.db.session import async_session_maker, engine
from ratatosk.endpoints.db_manipulation.conversations.export import _build_zip_archive
from ratatosk.providers.provider import (
    AutoMode,
    EcoMode,
    FixedMode,
    FullMode,
    NoneMode,
)
from ratatosk.providers.ratatosk import RatatoskProvider


class TestConversationsSuite(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.alice = User(username="__ut_alice__", is_active=True, is_admin=False)
        self.bob = User(username="__ut_bob__", is_active=True, is_admin=False)
        self.admin = User(username="__ut_admin__", is_active=True, is_admin=True)
        self.created_conv_ids: list[str] = []

        async with async_session_maker() as session:
            # Clean up any leftover test users from interrupted runs
            await session.execute(
                delete(User).where(
                    User.username.in_(["__ut_alice__", "__ut_bob__", "__ut_admin__"])
                )
            )
            session.add_all([self.alice, self.bob, self.admin])
            await session.commit()
            for u in (self.alice, self.bob, self.admin):
                await session.refresh(u)

            self.base_time = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)

            self.conv_alice = Conversation(
                user_id=self.alice.id,
                title="Alice Main Conv",
                ai_notes="User is testing Ratatosk.",
                analyzed_at=self.base_time + timedelta(seconds=4),
                title_auto=False,
                archived=False,
                created_at=self.base_time,
            )
            self.conv_empty = Conversation(
                user_id=self.alice.id,
                title="Alice Empty Conv",
                archived=False,
                created_at=self.base_time - timedelta(minutes=10),
            )
            self.conv_archived = Conversation(
                user_id=self.alice.id,
                title="Alice Archived Conv",
                archived=True,
                created_at=self.base_time - timedelta(minutes=20),
            )
            self.conv_bob = Conversation(
                user_id=self.bob.id,
                title="Bob Private Conv",
                archived=False,
                created_at=self.base_time + timedelta(minutes=5),
            )
            session.add_all(
                [self.conv_alice, self.conv_empty, self.conv_archived, self.conv_bob]
            )
            await session.commit()
            for c in (
                self.conv_alice,
                self.conv_empty,
                self.conv_archived,
                self.conv_bob,
            ):
                await session.refresh(c)

            self.alice_msgs: list[Message] = []
            for i in range(10):
                m = Message(
                    conversation_id=self.conv_alice.id,
                    role="user" if i % 2 == 0 else "assistant",
                    model="gemma-4-31b-it",
                    content=f"Message #{i}",
                    parts=[{"text": f"Message #{i}"}] if i % 2 == 1 else None,
                    token_count=100,
                    cost=0.0002,
                    created_at=self.base_time + timedelta(seconds=i),
                )
                self.alice_msgs.append(m)

            self.bob_msg = Message(
                conversation_id=self.conv_bob.id,
                role="user",
                model="gemma-4-31b-it",
                content="Bob secret",
                token_count=15,
                cost=0.00003,
                created_at=self.base_time + timedelta(minutes=6),
            )
            session.add_all([*self.alice_msgs, self.bob_msg])
            await session.commit()
            for m in self.alice_msgs:
                await session.refresh(m)
            await session.refresh(self.bob_msg)

        self.alice_headers = {
            "Authorization": f"Bearer {create_access_token(self.alice.id)}"
        }
        self.bob_headers = {
            "Authorization": f"Bearer {create_access_token(self.bob.id)}"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {create_access_token(self.admin.id)}"
        }
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        async with async_session_maker() as session:
            if self.created_conv_ids:
                await session.execute(
                    delete(Conversation).where(
                        Conversation.id.in_(self.created_conv_ids)
                    )
                )
            await session.execute(
                delete(User).where(
                    User.id.in_([self.alice.id, self.bob.id, self.admin.id])
                )
            )
            await session.commit()
        await engine.dispose()

    # =========================================================================
    # 1. DB LAYER: history.py & BaseProvider.generate_context
    # =========================================================================

    async def test_01_save_message_and_history_queries(self) -> None:
        # Auto-create conversation when conversation_id is None
        conv_id, msg1_id = await save_message(
            user_id=self.alice.id,
            conversation_id=None,
            role="user",
            model="gemma-4-31b-it",
            content="Hello world",
            token_count=12,
            cost=0.0001,
        )
        self.created_conv_ids.append(conv_id)
        self.assertIsNotNone(conv_id)
        self.assertIsNotNone(msg1_id)

        # Append second message to existing conversation
        same_conv_id, msg2_id = await save_message(
            user_id=self.alice.id,
            conversation_id=conv_id,
            role="assistant",
            model="gemma-4-31b-it",
            content="Hi Alice!",
            parts=[{"text": "Hi Alice!"}],
            token_count=20,
            cost=0.0002,
        )
        self.assertEqual(conv_id, same_conv_id)
        self.assertNotEqual(msg1_id, msg2_id)

        # Verify all 4 history retrieval functions on self.conv_alice (M0..M9, 100 tokens each)
        full = await get_full_history(self.conv_alice.id)
        self.assertEqual([m.content for m in full], [f"Message #{i}" for i in range(10)])

        last_3 = await get_history_by_number(self.conv_alice.id, 3)
        self.assertEqual([m.content for m in last_3], ["Message #7", "Message #8", "Message #9"])

        # Each message has 100 tokens -> budget 350 fits last 3 messages (300 <= 350 < 400)
        by_tok = await get_history_by_token(self.conv_alice.id, 350)
        self.assertEqual([m.content for m in by_tok], ["Message #7", "Message #8", "Message #9"])

        # analyzed_at is base_time + 4s -> strictly after M4 means M5..M9
        since_analysis = await get_history_since_analysis(self.conv_alice.id)
        self.assertEqual(
            [m.content for m in since_analysis],
            ["Message #5", "Message #6", "Message #7", "Message #8", "Message #9"],
        )

    async def test_02_generate_context_modes(self) -> None:
        provider = RatatoskProvider()

        # EcoMode: includes AI notes + messages after analyzed_at (M5..M9)
        ctx_eco = await provider.generate_context(self.conv_alice.id, EcoMode())
        self.assertIn("System prompts", ctx_eco)
        self.assertEqual(ctx_eco["conversation title"], "Alice Main Conv")
        self.assertEqual(ctx_eco["AI notes"], "User is testing Ratatosk.")
        self.assertEqual(len(ctx_eco["history"]), 5)

        # AutoMode(): 1000-token budget fits all 10 messages (10 * 100 <= 1000)
        ctx_auto = await provider.generate_context(self.conv_alice.id, AutoMode())
        self.assertEqual(ctx_auto["AI notes"], "User is testing Ratatosk.")
        self.assertEqual(len(ctx_auto["history"]), 10)

        # FixedMode(n=4): last 4 messages (M6..M9)
        ctx_fixed = await provider.generate_context(
            self.conv_alice.id, FixedMode(n=4)
        )
        self.assertEqual(
            [m.content for m in ctx_fixed["history"]],
            ["Message #6", "Message #7", "Message #8", "Message #9"],
        )

        # FullMode: all 10 messages
        ctx_full = await provider.generate_context(self.conv_alice.id, FullMode())
        self.assertEqual(len(ctx_full["history"]), 10)

        # NoneMode: empty history
        ctx_none = await provider.generate_context(self.conv_alice.id, NoneMode())
        self.assertEqual(ctx_none["history"], [])
        self.assertEqual(ctx_none["conversation title"], "Alice Main Conv")

        # Brand-new conversation (conversation_id=None)
        ctx_new = await provider.generate_context(None, EcoMode())
        self.assertEqual(ctx_new["history"], [])
        self.assertEqual(ctx_new["conversation title"], "New Conversation")
        self.assertEqual(ctx_new["AI notes"], "")

    # =========================================================================
    # 2. AUTHENTICATION GUARD
    # =========================================================================

    async def test_03_unauthenticated_requests_rejected(self) -> None:
        endpoints = [
            ("GET", "/db/conversations/list"),
            ("GET", f"/db/conversations/manager?conversation_id={self.conv_alice.id}"),
            ("GET", f"/db/conversations/messages?conversation_id={self.conv_alice.id}"),
            ("PATCH", f"/db/conversations?conversation_id={self.conv_alice.id}"),
            ("PATCH", f"/db/conversations/anchor?conversation_id={self.conv_alice.id}"),
            ("GET", f"/db/conversations/export?conversation_id={self.conv_alice.id}"),
            ("DELETE", f"/db/conversations?conversation_id={self.conv_alice.id}"),
        ]
        for method, url in endpoints:
            r = await self.client.request(method, url)
            self.assertEqual(r.status_code, 401, f"Expected 401 on {method} {url}")

    # =========================================================================
    # 3. GET /db/conversations/list
    # =========================================================================

    async def test_04_list_conversations_isolation_and_filters(self) -> None:
        # Alice sees only her non-archived conversations, sorted by activity desc
        r = await self.client.get("/db/conversations/list", headers=self.alice_headers)
        self.assertEqual(r.status_code, 200)
        items = r.json()
        self.assertEqual([c["id"] for c in items], [self.conv_alice.id, self.conv_empty.id])
        self.assertEqual(items[0]["nb_message"], 10)
        self.assertEqual(items[1]["nb_message"], 0)
        self.assertIsNone(items[1]["last_message"])

        # Include archived
        r = await self.client.get(
            "/db/conversations/list",
            params={"only_not_archived": False},
            headers=self.alice_headers,
        )
        self.assertEqual(
            [c["id"] for c in r.json()],
            [self.conv_alice.id, self.conv_empty.id, self.conv_archived.id],
        )

        # Non-admin blocked from querying another user's ID
        r = await self.client.get(
            "/db/conversations/list",
            params={"user_id": self.bob.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 403)

        # Admin can filter by Bob's user_id
        r = await self.client.get(
            "/db/conversations/list",
            params={"user_id": self.bob.id},
            headers=self.admin_headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c["id"] for c in r.json()], [self.conv_bob.id])

    # =========================================================================
    # 4. GET /db/conversations/manager & PATCH /anchor
    # =========================================================================

    async def test_05_manager_and_anchor_lifecycle(self) -> None:
        # Empty conversation -> None anchors
        r = await self.client.get(
            "/db/conversations/manager",
            params={"conversation_id": self.conv_empty.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {
                "id": self.conv_empty.id,
                "title": "Alice Empty Conv",
                "title_auto": True,
                "archived": False,
                "anchor_message": None,
                "anchor_message_index": None,
                "nb_message": 0,
            },
        )

        # Default (cache_anchor=None) -> points to M9 (index 9)
        r = await self.client.get(
            "/db/conversations/manager",
            params={"conversation_id": self.conv_alice.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r.json()["anchor_message"], self.alice_msgs[9].id)
        self.assertEqual(r.json()["anchor_message_index"], 9)

        # Set anchor to M3 via PATCH /anchor
        r = await self.client.patch(
            "/db/conversations/anchor",
            params={
                "conversation_id": self.conv_alice.id,
                "anchor_id": self.alice_msgs[3].id,
            },
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["anchor_message"], self.alice_msgs[3].id)
        self.assertEqual(r.json()["anchor_message_index"], 3)

        # Reset anchor to None -> back to M9 (index 9)
        r = await self.client.patch(
            "/db/conversations/anchor",
            params={"conversation_id": self.conv_alice.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["anchor_message"], self.alice_msgs[9].id)
        self.assertEqual(r.json()["anchor_message_index"], 9)

        # Stale anchor in DB (deleted message UUID) -> graceful fallback to M9
        async with async_session_maker() as session:
            c = await session.get(Conversation, self.conv_alice.id)
            c.cache_anchor = "00000000-0000-0000-0000-000000000000"
            await session.commit()

        r = await self.client.get(
            "/db/conversations/manager",
            params={"conversation_id": self.conv_alice.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r.json()["anchor_message"], self.alice_msgs[9].id)
        self.assertEqual(r.json()["anchor_message_index"], 9)

        # Security: Bob gets 403 on Alice's conversation & anchor (even with bogus message ID)
        r = await self.client.patch(
            "/db/conversations/anchor",
            params={"conversation_id": self.conv_alice.id, "anchor_id": "bogus"},
            headers=self.bob_headers,
        )
        self.assertEqual(r.status_code, 403)

        # Foreign message ID rejected with 404
        r = await self.client.patch(
            "/db/conversations/anchor",
            params={
                "conversation_id": self.conv_alice.id,
                "anchor_id": self.bob_msg.id,
            },
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 404)

    # =========================================================================
    # 5. GET /db/conversations/messages (Bidirectional Staircase Pagination)
    # =========================================================================

    async def test_06_messages_staircase_pagination(self) -> None:
        # Default (no cursor, nb_requested=4) -> [M6, M7, M8, M9]
        r = await self.client.get(
            "/db/conversations/messages",
            params={"conversation_id": self.conv_alice.id, "nb_requested": 4},
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 200)
        msgs = r.json()
        self.assertEqual([m["content"] for m in msgs], [f"Message #{i}" for i in range(6, 10)])
        self.assertEqual([m["is_last"] for m in msgs], [False, False, False, True])
        self.assertEqual([m["is_first"] for m in msgs], [False, False, False, False])

        # AROUND M4 (nb_requested=4) -> [M2, M3, M4, M5]
        r = await self.client.get(
            "/db/conversations/messages",
            params={
                "conversation_id": self.conv_alice.id,
                "nb_requested": 4,
                "ref_message": "around",
                "ref_message_id": self.alice_msgs[4].id,
            },
            headers=self.alice_headers,
        )
        msgs = r.json()
        self.assertEqual([m["content"] for m in msgs], [f"Message #{i}" for i in range(2, 6)])

        # BEFORE M2 (nb_requested=5) -> [M0, M1] with M0.is_first=True
        r = await self.client.get(
            "/db/conversations/messages",
            params={
                "conversation_id": self.conv_alice.id,
                "nb_requested": 5,
                "ref_message": "before",
                "ref_message_id": self.alice_msgs[2].id,
            },
            headers=self.alice_headers,
        )
        msgs = r.json()
        self.assertEqual([m["content"] for m in msgs], ["Message #0", "Message #1"])
        self.assertTrue(msgs[0]["is_first"])
        self.assertFalse(msgs[1]["is_first"])

        # BEFORE M0 -> []
        r = await self.client.get(
            "/db/conversations/messages",
            params={
                "conversation_id": self.conv_alice.id,
                "ref_message": "before",
                "ref_message_id": self.alice_msgs[0].id,
            },
            headers=self.alice_headers,
        )
        self.assertEqual(r.json(), [])

        # AFTER M7 (nb_requested=5) -> [M8, M9] with M9.is_last=True
        r = await self.client.get(
            "/db/conversations/messages",
            params={
                "conversation_id": self.conv_alice.id,
                "nb_requested": 5,
                "ref_message": "after",
                "ref_message_id": self.alice_msgs[7].id,
            },
            headers=self.alice_headers,
        )
        msgs = r.json()
        self.assertEqual([m["content"] for m in msgs], ["Message #8", "Message #9"])
        self.assertTrue(msgs[1]["is_last"])

        # AFTER M9 -> []
        r = await self.client.get(
            "/db/conversations/messages",
            params={
                "conversation_id": self.conv_alice.id,
                "ref_message": "after",
                "ref_message_id": self.alice_msgs[9].id,
            },
            headers=self.alice_headers,
        )
        self.assertEqual(r.json(), [])

        # Validation & security checks
        r_bad_ref = await self.client.get(
            "/db/conversations/messages",
            params={"conversation_id": self.conv_alice.id, "ref_message_id": self.bob_msg.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r_bad_ref.status_code, 404)

        r_bad_limit = await self.client.get(
            "/db/conversations/messages",
            params={"conversation_id": self.conv_alice.id, "nb_requested": 201},
            headers=self.alice_headers,
        )
        self.assertEqual(r_bad_limit.status_code, 422)

        r_forbidden = await self.client.get(
            "/db/conversations/messages",
            params={"conversation_id": self.conv_alice.id},
            headers=self.bob_headers,
        )
        self.assertEqual(r_forbidden.status_code, 403)

    # =========================================================================
    # 6. PATCH /db/conversations
    # =========================================================================

    async def test_07_patch_conversation(self) -> None:
        # Partial update + explicit null ignored safely via exclude_none=True
        r = await self.client.patch(
            "/db/conversations",
            params={"conversation_id": self.conv_alice.id},
            json={"title": "Nouveau Titre ✨", "archived": True, "title_auto": None},
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 200)
        mgr = r.json()
        self.assertEqual(mgr["title"], "Nouveau Titre ✨")
        self.assertTrue(mgr["archived"])
        self.assertFalse(mgr["title_auto"])

        # Empty body no-op
        r_noop = await self.client.patch(
            "/db/conversations",
            params={"conversation_id": self.conv_alice.id},
            json={},
            headers=self.alice_headers,
        )
        self.assertEqual(r_noop.status_code, 200)
        self.assertEqual(r_noop.json()["title"], "Nouveau Titre ✨")

        # Forbidden for Bob, 404 for unknown
        r_bob = await self.client.patch(
            "/db/conversations",
            params={"conversation_id": self.conv_alice.id},
            json={"title": "Nope"},
            headers=self.bob_headers,
        )
        self.assertEqual(r_bob.status_code, 403)

        r_404 = await self.client.patch(
            "/db/conversations",
            params={"conversation_id": "unknown-id"},
            json={"title": "Nope"},
            headers=self.alice_headers,
        )
        self.assertEqual(r_404.status_code, 404)

    # =========================================================================
    # 7. GET /db/conversations/export (.md & .zip)
    # =========================================================================

    async def test_08_export_markdown_and_zip(self) -> None:
        async with async_session_maker() as session:
            c = await session.get(Conversation, self.conv_alice.id)
            c.title = "Export Écureuil 🐿️ : Démo"
            rich_msg = Message(
                conversation_id=self.conv_alice.id,
                role="assistant",
                model="gemini-2.5-pro",
                content="### Titre dans la bulle\n\nTexte en **gras** :\n\n```python\nx = 42\n```",
                parts=[
                    {"thought": True, "text": "Réflexion interne du modèle."},
                    {"tool_call": {"name": "search_docs", "args": {"q": "ratatosk"}}},
                    {
                        "text": "### Titre dans la bulle\n\nTexte en **gras** :\n\n```python\nx = 42\n```"
                    },
                ],
                created_at=self.base_time + timedelta(seconds=20),
            )
            session.add(rich_msg)
            await session.commit()

        old_name = dynamic_settings.agent_name
        dynamic_settings.update(DynamicSettingsUpdate(agent_name="CustomRatatosk"))
        try:
            r = await self.client.get(
                "/db/conversations/export",
                params={"conversation_id": self.conv_alice.id},
                headers=self.alice_headers,
            )
        finally:
            dynamic_settings.update(DynamicSettingsUpdate(agent_name=old_name))

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("text/markdown"))
        self.assertIn("filename*=UTF-8''", r.headers["content-disposition"])

        md = r.text
        self.assertIn("# Export Écureuil 🐿️ : Démo", md)
        self.assertIn("### 👤 __ut_alice__", md)
        self.assertIn("### 🤖 CustomRatatosk (`gemini-2.5-pro`)", md)
        self.assertIn("<details>\n<summary>thinking</summary>\n\nRéflexion interne du modèle.\n\n</details>", md)
        self.assertIn("<details>\n<summary>tool calls</summary>", md)
        self.assertIn("> ### Titre dans la bulle\n>\n> Texte en **gras** :\n>\n> ```python\n> x = 42\n> ```", md)

        # Verify ZIP archive helper with attachment file
        with tempfile.TemporaryDirectory() as tmp:
            sample_file = Path(tmp) / "diagram.png"
            sample_file.write_bytes(b"\x89PNG\r\n\x1a\n")
            zip_bytes = _build_zip_archive(
                "Export.md", md, [("diagram.png", sample_file)]
            )
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                self.assertEqual(
                    sorted(zf.namelist()),
                    ["Export.md", "attachments/diagram.png"],
                )
                self.assertEqual(zf.read("attachments/diagram.png"), b"\x89PNG\r\n\x1a\n")

        # Bob forbidden (403) & empty conversation export (200)
        r_bob = await self.client.get(
            "/db/conversations/export",
            params={"conversation_id": self.conv_alice.id},
            headers=self.bob_headers,
        )
        self.assertEqual(r_bob.status_code, 403)

        r_empty = await self.client.get(
            "/db/conversations/export",
            params={"conversation_id": self.conv_empty.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r_empty.status_code, 200)
        self.assertIn("- **Messages**: 0", r_empty.text)

    # =========================================================================
    # 8. DELETE /db/conversations (PostgreSQL + SQLite CASCADE)
    # =========================================================================

    async def test_09_delete_conversation_and_cascade(self) -> None:
        # Bob forbidden
        r_bob = await self.client.delete(
            "/db/conversations",
            params={"conversation_id": self.conv_alice.id},
            headers=self.bob_headers,
        )
        self.assertEqual(r_bob.status_code, 403)

        # Alice deletes conv_alice -> 200 & 0 orphan messages in DB
        r_del = await self.client.delete(
            "/db/conversations",
            params={"conversation_id": self.conv_alice.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r_del.status_code, 200)

        async with async_session_maker() as session:
            orphans = (
                await session.execute(
                    select(Message.id).where(
                        Message.conversation_id == self.conv_alice.id
                    )
                )
            ).scalars().all()
            self.assertEqual(orphans, [])

        # Deleting again -> 404
        r_404 = await self.client.delete(
            "/db/conversations",
            params={"conversation_id": self.conv_alice.id},
            headers=self.alice_headers,
        )
        self.assertEqual(r_404.status_code, 404)

    async def test_10_sqlite_pragma_cascade(self) -> None:
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @event.listens_for(sqlite_engine.sync_engine, "connect")
        def _fk_on(dbapi_conn, _rec) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        sqlite_session = async_sessionmaker(
            sqlite_engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with sqlite_engine.begin() as conn:
                self.assertEqual(
                    (await conn.execute(text("PRAGMA foreign_keys"))).scalar(), 1
                )
                await conn.run_sync(Base.metadata.create_all)

            async with sqlite_session() as s:
                u = User(username="local_u")
                s.add(u)
                await s.commit()
                await s.refresh(u)

                c = Conversation(user_id=u.id, title="Local")
                s.add(c)
                await s.commit()
                await s.refresh(c)

                s.add(Message(conversation_id=c.id, role="user", model="m", content="hi"))
                await s.commit()

                await s.delete(c)
                await s.commit()

                rem = (await s.execute(select(Message.id))).scalars().all()
                self.assertEqual(rem, [])
        finally:
            await sqlite_engine.dispose()


if __name__ == "__main__":
    unittest.main()
