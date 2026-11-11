import asyncio
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import httpx
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import delete

from ratatosk.app import app
from ratatosk.core.config import settings
from ratatosk.core.security import create_access_token
from ratatosk.db.models import Attachment, Conversation, User
from ratatosk.db.session import async_session_maker, engine
from ratatosk.providers import provider
from ratatosk.providers.schemas import (
    AttachmentEvent,
    DoneEvent,
    ImageProgressEvent,
    ToolResultEvent,
)
from ratatosk.tools import (
    IMAGE_GENERATION_TASK,
    AFCToolRegistry,
    BuiltinToolRegistry,
    ToolContext,
    ToolVisibility,
    afc_tool,
    build_generate_image_declaration,
    builtin_registry,
    extract_grounding_sources,
    extract_image_from_html,
    fetch_and_store_web_image,
    resolve_delegation_models,
)


def _make_png(width: int = 400, height: int = 300) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
    )


class TestAFCToolsAndWebSearch(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._patcher = patch.object(settings, "app_dir", Path(self._tmp.name))
        self._patcher.start()

        self.user = User(username="__ut_afc_user__", is_active=True, is_admin=False)
        self.admin = User(username="__ut_afc_admin__", is_active=True, is_admin=True)
        async with async_session_maker() as session:
            await session.execute(
                delete(User).where(
                    User.username.in_(["__ut_afc_user__", "__ut_afc_admin__"])
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
        uids = [self.user.id, self.admin.id]
        async with async_session_maker() as session:
            await session.execute(delete(User).where(User.id.in_(uids)))
            await session.execute(
                delete(Attachment).where(
                    Attachment.user_id.in_(uids) | Attachment.user_id.is_(None)
                )
            )
            await session.commit()
        await engine.dispose()
        self._patcher.stop()
        self._tmp.cleanup()

    def test_01_afc_registry_and_grounding_extraction(self) -> None:
        reg = AFCToolRegistry()

        @afc_tool(name="custom_calc")
        def sample_fn(x: int) -> int:
            return x * 2

        reg.register(sample_fn, name="local_calc")
        self.assertIs(reg.get("local_calc"), sample_fn)
        self.assertEqual(reg.list_callables(["local_calc"]), [sample_fn])

        html = (
            "<html><head>"
            '<meta property="og:image" content="/assets/ratatosk_hero.png">'
            "</head><body></body></html>"
        )
        self.assertEqual(
            extract_image_from_html(html, "https://example.org/docs/intro"),
            "https://example.org/assets/ratatosk_hero.png",
        )

        grounding = SimpleNamespace(
            web_search_queries=["ratatosk mythologie", "ratatosk mythologie"],
            grounding_chunks=[
                SimpleNamespace(
                    web=SimpleNamespace(
                        uri="https://en.wikipedia.org/wiki/Ratatoskr",
                        title="Ratatoskr - Wikipedia",
                    )
                ),
                SimpleNamespace(
                    web=SimpleNamespace(
                        uri="https://en.wikipedia.org/wiki/Ratatoskr",
                        title="Duplicate",
                    )
                ),
            ],
        )
        queries, sources = extract_grounding_sources(grounding)
        self.assertEqual(queries, ["ratatosk mythologie"])
        self.assertEqual(
            sources,
            [
                {
                    "title": "Ratatoskr - Wikipedia",
                    "url": "https://en.wikipedia.org/wiki/Ratatoskr",
                }
            ],
        )

    async def test_02_fetch_and_store_web_image_from_html_og_image(self) -> None:
        png_bytes = _make_png(640, 480)

        def _mock_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/article":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html; charset=utf-8"},
                    text='<head><meta property="og:image" content="https://cdn.example.org/squirrel.png"></head>',
                )
            if request.url.path == "/squirrel.png":
                return httpx.Response(
                    200,
                    headers={"content-type": "image/png"},
                    content=png_bytes,
                )
            return httpx.Response(404)

        mock_http = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
        try:
            att1 = await fetch_and_store_web_image(
                "https://example.org/article",
                user_id=self.user.id,
                title="Yggdrasil Squirrel",
                client=mock_http,
            )
            self.assertIsNotNone(att1)
            assert att1 is not None
            self.assertFalse(att1.is_generated)
            self.assertEqual(att1.source, "tool:web_search")
            self.assertEqual(att1.external_uri, "https://example.org/article")
            self.assertEqual((att1.width, att1.height), (640, 480))

            # Deduplication on second fetch
            att2 = await fetch_and_store_web_image(
                "https://example.org/article",
                user_id=self.user.id,
                title="Yggdrasil Squirrel",
                client=mock_http,
            )
            assert att2 is not None
            self.assertEqual(att1.id, att2.id)
        finally:
            await mock_http.aclose()

    async def test_03_three_search_modes_sources_and_web_image_in_chat_stream(
        self,
    ) -> None:
        png_bytes = _make_png(500, 400)
        up = await self.client.post(
            "/db/attachments/upload",
            headers=self.headers,
            files={"file": ("user_note.png", png_bytes, "image/png")},
        )
        user_att_id = up.json()["id"]

        captured_configs: list[dict] = []

        async def _fake_generate_content_stream(*, model: str, contents: list, config: dict):
            captured_configs.append(config)

            async def _gen():
                yield SimpleNamespace(
                    model_version=model,
                    candidates=[
                        SimpleNamespace(
                            content=SimpleNamespace(
                                parts=[
                                    SimpleNamespace(
                                        thought=False,
                                        text="Ratatosk court sur Yggdrasil.",
                                        function_call=None,
                                    )
                                ]
                            ),
                            grounding_metadata=(
                                SimpleNamespace(
                                    web_search_queries=["ratatosk yggdrasil"],
                                    grounding_chunks=[
                                        SimpleNamespace(
                                            web=SimpleNamespace(
                                                uri="https://myth.example.org/ratatosk",
                                                title="Encyclopédie Nordique",
                                            )
                                        )
                                    ],
                                )
                                if "tools" in config
                                else None
                            ),
                        )
                    ],
                    usage_metadata=SimpleNamespace(
                        prompt_token_count=20,
                        candidates_token_count=10,
                        thoughts_token_count=0,
                    ),
                )

            return _gen()

        async def _fake_fetch_web_img(url: str, *, user_id=None, title=None, source_page_url=None):
            def _handler(req: httpx.Request) -> httpx.Response:
                return httpx.Response(200, headers={"content-type": "image/png"}, content=png_bytes)

            async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as c:
                return await fetch_and_store_web_image(
                    "https://myth.example.org/img.png",
                    user_id=user_id,
                    title=title,
                    source_page_url=source_page_url,
                    client=c,
                )

        google_prov = provider._subproviders[0]
        fake_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=_fake_generate_content_stream)
        )

        with (
            patch.object(google_prov, "is_available", return_value=True),
            patch.object(google_prov, "_client", SimpleNamespace(aio=fake_aio)),
            patch(
                "ratatosk.providers.google.provider.fetch_and_store_web_image",
                side_effect=_fake_fetch_web_img,
            ),
        ):
            # 1. Mode "no_search" + enable_builtin_tools=False -> no tools in config
            r_no = await self.client.post(
                "/chat/stream",
                headers=self.headers,
                json={
                    "model": "gemini-2.5-flash",
                    "search_mode": "no_search",
                    "enable_builtin_tools": False,
                    "messages": [{"role": "user", "content": "Salut"}],
                },
            )
            self.assertEqual(r_no.status_code, 200)
            self.assertNotIn("tools", captured_configs[-1])

            # 2. Mode "full_search" with user attachment -> tools + directive + AttachmentEvent + SourcesEvent
            r_full = await self.client.post(
                "/chat/stream",
                headers=self.headers,
                json={
                    "model": "gemini-2.5-flash",
                    "search_mode": "full_search",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Qui est Ratatosk ?",
                            "attachments": [{"id": user_att_id, "filename": "user_note.png"}],
                        }
                    ],
                },
            )
            self.assertEqual(r_full.status_code, 200)
            cfg = captured_configs[-1]
            self.assertIn({"google_search": {}}, cfg["tools"])
            self.assertIn({"url_context": {}}, cfg["tools"])
            self.assertIn("<search_directive>", cfg.get("system_instruction", ""))

            events = [
                json.loads(line.removeprefix("data:").strip())
                for line in r_full.text.splitlines()
                if line.startswith("data:")
            ]
            event_types = [e["type"] for e in events]
            self.assertIn("attachment", event_types)
            self.assertIn("sources", event_types)
            self.assertIn("done", event_types)

            att_ev = next(e for e in events if e["type"] == "attachment")
            self.assertFalse(att_ev["is_generated"])
            self.assertEqual(att_ev["external_uri"], "https://myth.example.org/ratatosk")

            src_ev = next(e for e in events if e["type"] == "sources")
            kinds = [item["kind"] for item in src_ev["items"]]
            self.assertEqual(kinds, ["attachment", "web"])

            conv_id = next(e for e in events if e["type"] == "done")["conversation_id"]

            # 3. Export conversation -> ZIP includes both images and <summary>sources</summary>
            r_exp = await self.client.get(
                "/db/conversations/export",
                params={"conversation_id": conv_id},
                headers=self.headers,
            )
            self.assertEqual(r_exp.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(r_exp.content), "r") as zf:
                md_name = next(n for n in zf.namelist() if n.endswith(".md"))
                md_content = zf.read(md_name).decode("utf-8")
                self.assertIn("<summary>sources</summary>", md_content)
                self.assertIn(
                    "[Encyclopédie Nordique](https://myth.example.org/ratatosk)",
                    md_content,
                )

    async def test_04_builtin_tool_kornak_visibility_and_create_file_loop(self) -> None:
        reg = BuiltinToolRegistry()

        @reg.register(visibility=ToolVisibility.ACTIVE)
        def public_echo(msg: str, ctx: ToolContext) -> dict:
            """Public active tool."""
            return {"echo": msg, "user": ctx.user_id}

        @reg.register(visibility=ToolVisibility.KORNAK)
        def hidden_close_ui(reason: str = "bye") -> dict:
            """Dormant Kornak tool."""
            return {"closed": reason}

        # 1. Kornak visibility filtering: hidden_close_ui is omitted unless unlocked
        default_decls = reg.get_google_declarations()
        self.assertEqual([d["name"] for d in default_decls], ["public_echo"])
        # ToolContext (`ctx`) must never leak into the LLM JSON Schema
        self.assertNotIn("ctx", default_decls[0]["parameters_json_schema"]["properties"])

        unlocked_decls = reg.get_google_declarations(unlocked_tools=["hidden_close_ui"])
        self.assertEqual(
            [d["name"] for d in unlocked_decls],
            ["public_echo", "hidden_close_ui"],
        )

        # 2. End-to-end chat stream where Gemini calls `create_file` then answers
        round_counter = 0

        async def _fake_stream_with_create_file(*, model: str, contents: list, config: dict):
            nonlocal round_counter
            round_counter += 1
            current_round = round_counter

            async def _gen():
                if current_round == 1:
                    yield SimpleNamespace(
                        model_version=model,
                        candidates=[
                            SimpleNamespace(
                                content=SimpleNamespace(
                                    parts=[
                                        SimpleNamespace(
                                            thought=False,
                                            text=None,
                                            function_call=SimpleNamespace(
                                                id="call_cf_1",
                                                name="create_file",
                                                args={
                                                    "filename": "fiche_revision.md",
                                                    "content": "# Fiche Révision\n- Point 1\n- Point 2\n",
                                                    "description": "Fiche de révision générée",
                                                },
                                            ),
                                        )
                                    ]
                                ),
                                grounding_metadata=None,
                            )
                        ],
                        usage_metadata=SimpleNamespace(
                            prompt_token_count=15,
                            candidates_token_count=12,
                            thoughts_token_count=0,
                        ),
                    )
                else:
                    yield SimpleNamespace(
                        model_version=model,
                        candidates=[
                            SimpleNamespace(
                                content=SimpleNamespace(
                                    parts=[
                                        SimpleNamespace(
                                            thought=False,
                                            text="Voici ta fiche de révision prête à télécharger !",
                                            function_call=None,
                                        )
                                    ]
                                ),
                                grounding_metadata=None,
                            )
                        ],
                        usage_metadata=SimpleNamespace(
                            prompt_token_count=30,
                            candidates_token_count=10,
                            thoughts_token_count=0,
                        ),
                    )

            return _gen()

        google_prov = provider._subproviders[0]
        fake_aio = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=_fake_stream_with_create_file)
        )

        with (
            patch.object(google_prov, "is_available", return_value=True),
            patch.object(google_prov, "_client", SimpleNamespace(aio=fake_aio)),
        ):
            r_cf = await self.client.post(
                "/chat/stream",
                headers=self.headers,
                json={
                    "model": "gemini-2.5-flash",
                    "search_mode": "no_search",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Crée-moi un fichier fiche_revision.md",
                        }
                    ],
                },
            )
            self.assertEqual(r_cf.status_code, 200)

        events = [
            json.loads(line.removeprefix("data:").strip())
            for line in r_cf.text.splitlines()
            if line.startswith("data:")
        ]
        types_seq = [e["type"] for e in events]
        self.assertEqual(
            types_seq,
            ["tool_call", "tool_result", "attachment", "text", "done"],
        )

        att_ev = next(e for e in events if e["type"] == "attachment")
        self.assertTrue(att_ev["is_generated"])
        self.assertEqual(att_ev["filename"], "fiche_revision.md")
        self.assertEqual(att_ev["mime_type"], "text/markdown")

        # Download the generated file via /db/attachments/full -> exact UTF-8 content
        r_dl = await self.client.get(
            "/db/attachments/full",
            params={"attachment_id": att_ev["id"]},
            headers=self.headers,
        )
        self.assertEqual(r_dl.status_code, 200)
        self.assertEqual(
            r_dl.text, "# Fiche Révision\n- Point 1\n- Point 2\n"
        )

    async def test_05_server_tools_reset_admin_guard_and_manage_conversation(
        self,
    ) -> None:
        # 1. `reset_server` visibility & admin guard
        user_decls = builtin_registry.get_google_declarations(
            unlocked_tools=["reset_server"], is_admin=False
        )
        self.assertNotIn("reset_server", [d["name"] for d in user_decls])

        admin_decls = builtin_registry.get_google_declarations(
            unlocked_tools=["reset_server"], is_admin=True
        )
        self.assertIn("reset_server", [d["name"] for d in admin_decls])

        # Non-admin execution is rejected even if invoked directly
        res_denied = await builtin_registry.execute(
            "reset_server",
            {"reason": "hack"},
            ToolContext(user_id=self.user.id, is_admin=False),
        )
        self.assertIn("Permission denied", res_denied.output.get("error", ""))

        # Admin execution schedules `_trigger_process_restart`
        with patch("ratatosk.tools.server._trigger_process_restart") as mock_restart:
            res_ok = await builtin_registry.execute(
                "reset_server",
                {"reason": "config_reload", "delay_seconds": 0.1},
                ToolContext(user_id=self.admin.id, is_admin=True),
            )
            self.assertEqual(res_ok.output["status"], "restarting")
            await asyncio.sleep(0.15)
            mock_restart.assert_called_once()

        # 2. `manage_conversation` accessible to standard user on their own conversations
        async with async_session_maker() as session:
            conv_user = Conversation(user_id=self.user.id, title="Brouillon Initial")
            conv_admin = Conversation(user_id=self.admin.id, title="Conv Admin")
            session.add_all([conv_user, conv_admin])
            await session.commit()
            await session.refresh(conv_user)
            await session.refresh(conv_admin)
            user_conv_id = conv_user.id
            admin_conv_id = conv_admin.id

        user_ctx = ToolContext(
            user_id=self.user.id, conversation_id=user_conv_id, is_admin=False
        )

        # Rename current conversation (omitting conversation_id uses ctx.conversation_id)
        res_rename = await builtin_registry.execute(
            "manage_conversation",
            {"action": "rename", "title": "Projet École 🐿️"},
            user_ctx,
        )
        self.assertEqual(res_rename.output["status"], "renamed")
        self.assertEqual(res_rename.output["title"], "Projet École 🐿️")

        # Archive & list
        res_arch = await builtin_registry.execute(
            "manage_conversation",
            {"action": "archive"},
            user_ctx,
        )
        self.assertTrue(res_arch.output["archived"])

        res_list = await builtin_registry.execute(
            "manage_conversation",
            {"action": "list", "only_not_archived": False},
            user_ctx,
        )
        self.assertTrue(
            any(
                c["id"] == user_conv_id and c["title"] == "Projet École 🐿️"
                for c in res_list.output["conversations"]
            )
        )

        # Standard user cannot delete Admin's conversation
        res_forbid = await builtin_registry.execute(
            "manage_conversation",
            {"action": "delete", "conversation_id": admin_conv_id},
            user_ctx,
        )
        self.assertIn("error", res_forbid.output)

        # Standard user deletes their own conversation
        res_del = await builtin_registry.execute(
            "manage_conversation",
            {"action": "delete", "conversation_id": user_conv_id},
            user_ctx,
        )
        self.assertEqual(res_del.output["status"], "deleted")

    async def test_06_cross_delegation_model_selection_and_progressive_denoising_stream(
        self,
    ) -> None:
        fake_google_catalog = {
            "gemini-2.5-flash": {
                "id": "gemini-2.5-flash",
                "display_name": "Gemini 2.5 Flash",
                "tasks": ["text-generation"],
                "tier": "featured",
                "is_recommended": True,
                "rank": 1,
            },
            "gemini-3.1-flash-image": {
                "id": "gemini-3.1-flash-image",
                "display_name": "Nano Banana 2",
                "tasks": ["text-to-image"],
                "tier": "featured",
                "is_recommended": True,
                "description": {"en": "Fast high-res image synthesis."},
                "pricing": {"input_per_1m": 0.5, "output_per_1m": 3.0},
                "rank": 7,
            },
            "gemini-3.1-flash-image-preview": {
                "id": "gemini-3.1-flash-image-preview",
                "display_name": "Nano Banana 2 Preview",
                "tasks": ["text-to-image"],
                "tier": "featured",
                "is_recommended": False,
                "rank": 8,
            },
            "gemini-3-pro-image": {
                "id": "gemini-3-pro-image",
                "display_name": "Nano Banana Pro",
                "tasks": ["text-to-image"],
                "tier": "standard",
                "is_recommended": False,
                "description": {
                    "en": "Pro artistic compositions and integrated typography."
                },
                "pricing": {"input_per_1m": 2.0, "output_per_1m": 12.0},
                "rank": 30,
            },
            "gemini-2.5-flash-image": {
                "id": "gemini-2.5-flash-image",
                "display_name": "Nano Banana Legacy",
                "tasks": ["text-to-image"],
                "tier": "legacy",
                "is_recommended": False,
                "rank": 61,
            },
        }
        fake_ollama_catalog = {
            "llama3.3": {
                "id": "llama3.3",
                "display_name": "Llama 3.3",
                "tasks": ["text-generation"],
                "tier": "standard",
            }
        }

        # 1. Intra-provider delegation (gemini-2.5-flash -> google text-to-image models)
        intra_cands = resolve_delegation_models(
            task=IMAGE_GENERATION_TASK,
            active_model="gemini-2.5-flash",
            active_provider_id="google",
            provider_catalogs={
                "google": fake_google_catalog,
                "ollama": fake_ollama_catalog,
            },
        )
        self.assertEqual(
            [c.id for c in intra_cands],
            ["gemini-3.1-flash-image", "gemini-3-pro-image"],
        )

        # 2. Cross-provider fallback (llama3.3 on ollama -> google text-to-image when allowed)
        cross_cands = resolve_delegation_models(
            task=IMAGE_GENERATION_TASK,
            active_model="llama3.3",
            active_provider_id="ollama",
            provider_catalogs={
                "ollama": fake_ollama_catalog,
                "google": fake_google_catalog,
            },
            allow_cross_provider=True,
        )
        self.assertEqual(cross_cands[0].id, "gemini-3.1-flash-image")

        cross_disabled = resolve_delegation_models(
            task=IMAGE_GENERATION_TASK,
            active_model="llama3.3",
            active_provider_id="ollama",
            provider_catalogs={
                "ollama": fake_ollama_catalog,
                "google": fake_google_catalog,
            },
            allow_cross_provider=False,
        )
        self.assertEqual(cross_disabled, [])

        # 3. Dynamic tool declaration check (enum + default + description)
        decl = build_generate_image_declaration(intra_cands)
        self.assertIsNotNone(decl)
        assert decl is not None
        self.assertIn("[DEFAULT, RECOMMENDED]", decl["description"])
        self.assertIn("Nano Banana Pro", decl["description"])
        model_prop = decl["parameters_json_schema"]["properties"]["model"]
        self.assertEqual(
            model_prop["enum"], ["gemini-3.1-flash-image", "gemini-3-pro-image"]
        )
        self.assertEqual(model_prop["default"], "gemini-3.1-flash-image")

        # 4. End-to-end streaming execution via GoogleProvider.chat_stream
        img_buf = io.BytesIO()
        Image.new("RGB", (64, 64), color=(40, 120, 200)).save(img_buf, format="PNG")
        real_png_bytes = img_buf.getvalue()

        google_sub = provider._subproviders[0]
        delegated_calls: list[tuple[str, Any, Any]] = []
        round_idx = 0

        async def fake_generate_content_stream(*, model, contents, config):
            nonlocal round_idx
            if model == "gemini-3-pro-image":
                delegated_calls.append((model, contents, config))

                async def _image_stream():
                    yield SimpleNamespace(
                        model_version=model,
                        candidates=[
                            SimpleNamespace(
                                content=SimpleNamespace(
                                    parts=[
                                        SimpleNamespace(
                                            thought=True,
                                            text="Composing Nordic squirrel typography layout...",
                                            inline_data=None,
                                        )
                                    ]
                                )
                            )
                        ],
                        usage_metadata=SimpleNamespace(
                            prompt_token_count=12,
                            candidates_token_count=0,
                            thoughts_token_count=6,
                        ),
                    )
                    yield SimpleNamespace(
                        model_version=model,
                        candidates=[
                            SimpleNamespace(
                                content=SimpleNamespace(
                                    parts=[
                                        SimpleNamespace(
                                            thought=False,
                                            text=None,
                                            inline_data=SimpleNamespace(
                                                data=real_png_bytes,
                                                mime_type="image/png",
                                            ),
                                        )
                                    ]
                                )
                            )
                        ],
                        usage_metadata=SimpleNamespace(
                            prompt_token_count=12,
                            candidates_token_count=100,
                            thoughts_token_count=6,
                        ),
                    )

                return _image_stream()

            round_idx += 1
            if round_idx == 1:
                fn_names = [
                    d["name"]
                    for t in config.get("tools", [])
                    for d in t.get("function_declarations", [])
                ]
                self.assertIn("generate_image", fn_names)

                async def _chat_round1():
                    yield SimpleNamespace(
                        model_version=model,
                        candidates=[
                            SimpleNamespace(
                                content=SimpleNamespace(
                                    parts=[
                                        SimpleNamespace(
                                            thought=False,
                                            text=None,
                                            function_call=SimpleNamespace(
                                                id="call_img_1",
                                                name="generate_image",
                                                args={
                                                    "prompt": "A Nordic squirrel on Yggdrasil with 'RATATOSK' title",
                                                    "model": "gemini-3-pro-image",
                                                    "aspect_ratio": "16:9",
                                                },
                                            ),
                                        )
                                    ]
                                ),
                                grounding_metadata=None,
                            )
                        ],
                        usage_metadata=SimpleNamespace(
                            prompt_token_count=20,
                            candidates_token_count=10,
                            thoughts_token_count=0,
                        ),
                    )

                return _chat_round1()

            async def _chat_round2():
                yield SimpleNamespace(
                    model_version=model,
                    candidates=[
                        SimpleNamespace(
                            content=SimpleNamespace(
                                parts=[
                                    SimpleNamespace(
                                        thought=False,
                                        text="Voici votre affiche générée avec Nano Banana Pro !",
                                        function_call=None,
                                    )
                                ]
                            ),
                            grounding_metadata=None,
                        )
                    ],
                    usage_metadata=SimpleNamespace(
                        prompt_token_count=35,
                        candidates_token_count=12,
                        thoughts_token_count=0,
                    ),
                )

            return _chat_round2()

        fake_client = SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(
                    generate_content_stream=fake_generate_content_stream
                )
            )
        )

        with (
            patch.object(google_sub, "_client", fake_client),
            patch.object(google_sub, "list_models", return_value=fake_google_catalog),
        ):
            events = [
                ev
                async for ev in google_sub.chat_stream(
                    model="gemini-2.5-flash",
                    messages=[
                        {
                            "role": "user",
                            "content": "Fais une affiche 16:9 de Ratatosk avec le modèle Pro",
                        }
                    ],
                    user_id=self.user.id,
                )
            ]

        self.assertEqual(len(delegated_calls), 1)
        self.assertEqual(delegated_calls[0][0], "gemini-3-pro-image")
        self.assertEqual(
            delegated_calls[0][2]["image_config"], {"aspect_ratio": "16:9"}
        )

        progress_events = [e for e in events if isinstance(e, ImageProgressEvent)]
        denoising_frames = [
            e for e in progress_events if e.preview_base64 is not None
        ]
        att_events = [e for e in events if isinstance(e, AttachmentEvent)]
        tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
        done_events = [e for e in events if isinstance(e, DoneEvent)]

        # Initial + thinking status + 3 progressive denoising frames + final 1.0 completion = 6 events
        self.assertGreaterEqual(len(progress_events), 5)
        self.assertEqual(len(denoising_frames), 3)
        self.assertEqual(
            [f.progress for f in denoising_frames],
            [0.35, 0.65, 0.9],
        )
        self.assertEqual(progress_events[-1].progress, 1.0)

        self.assertEqual(len(att_events), 1)
        self.assertTrue(att_events[0].is_generated)
        self.assertEqual(att_events[0].mime_type, "image/png")

        self.assertEqual(len(tool_results), 1)
        self.assertEqual(
            tool_results[0].result["delegated_model"], "gemini-3-pro-image"
        )
        self.assertEqual(tool_results[0].result["width"], 64)
        self.assertEqual(tool_results[0].result["height"], 64)
        self.assertEqual(len(done_events), 1)
        self.assertGreater(done_events[0].usage.cost, 0.0)


if __name__ == "__main__":
    unittest.main()
