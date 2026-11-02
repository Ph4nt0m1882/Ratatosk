import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from ratatosk.app import app
from ratatosk.core.security import create_access_token
from ratatosk.db.models import Conversation, User
from ratatosk.db.session import async_session_maker, engine
from ratatosk.providers import provider
from ratatosk.providers.google import GoogleProvider


def _make_chunk(
    parts: list[SimpleNamespace],
    model_version: str = "gemma-4-31b-it",
    prompt_tokens: int | None = None,
    candidates_tokens: int | None = None,
    thoughts_tokens: int | None = None,
) -> SimpleNamespace:
    usage = None
    if prompt_tokens is not None:
        usage = SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=candidates_tokens,
            thoughts_token_count=thoughts_tokens,
        )
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=parts))],
        model_version=model_version,
        usage_metadata=usage,
        text=None,
    )


def _parse_sse_lines(raw_body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event = "message"
    for line in raw_body.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current_event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            payload = json.loads(line.removeprefix("data:").strip())
            events.append((current_event, payload))
    return events


class TestChatSSESuite(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.alice = User(username="__ut_sse_alice__", is_active=True, is_admin=False)
        self.bob = User(username="__ut_sse_bob__", is_active=True, is_admin=False)

        async with async_session_maker() as session:
            await session.execute(
                delete(User).where(
                    User.username.in_(["__ut_sse_alice__", "__ut_sse_bob__"])
                )
            )
            session.add_all([self.alice, self.bob])
            await session.commit()
            await session.refresh(self.alice)
            await session.refresh(self.bob)

            self.conv_bob = Conversation(user_id=self.bob.id, title="Bob Conv")
            session.add(self.conv_bob)
            await session.commit()
            await session.refresh(self.conv_bob)

        self.alice_headers = {
            "Authorization": f"Bearer {create_access_token(self.alice.id)}"
        }

        # Ensure a GoogleProvider instance is registered even if no real API key is in .env
        self._orig_subproviders = list(provider._subproviders)
        self._google = next(
            (p for p in provider._subproviders if isinstance(p, GoogleProvider)),
            None,
        )
        if self._google is None:
            self._google = GoogleProvider()
            provider._subproviders.append(self._google)
        provider._models_cache.clear()

        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        provider._subproviders = self._orig_subproviders
        provider._models_cache.clear()
        async with async_session_maker() as session:
            await session.execute(
                delete(User).where(User.id.in_([self.alice.id, self.bob.id]))
            )
            await session.commit()
        await engine.dispose()

    async def test_01_pre_stream_http_guards(self) -> None:
        # Unknown model -> 404
        r = await self.client.post(
            "/chat/stream",
            json={"model": "unknown-model-xyz", "messages": [{"content": "Hi"}]},
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 404)

        # Unknown conversation_id -> 404
        r = await self.client.post(
            "/chat/stream",
            json={
                "model": "gemma-4-31b-it",
                "conversation_id": "non-existent-id",
                "messages": [{"content": "Hi"}],
            },
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 404)

        # Cross-user conversation_id -> 403
        r = await self.client.post(
            "/chat/stream",
            json={
                "model": "gemma-4-31b-it",
                "conversation_id": self.conv_bob.id,
                "messages": [{"content": "Hi"}],
            },
            headers=self.alice_headers,
        )
        self.assertEqual(r.status_code, 403)

    async def test_02_sse_stream_new_conv_multiturn_and_export(self) -> None:
        async def fake_stream_turn1(**_kwargs):
            yield _make_chunk(
                [SimpleNamespace(thought=True, text="Thinking step 1... ", function_call=None)]
            )
            yield _make_chunk(
                [
                    SimpleNamespace(
                        thought=False,
                        text=None,
                        function_call=SimpleNamespace(
                            id="call_1", name="calc", args={"x": 2}
                        ),
                    )
                ]
            )
            yield _make_chunk(
                [SimpleNamespace(thought=False, text="Bonjour ", function_call=None)]
            )
            yield _make_chunk(
                [SimpleNamespace(thought=False, text="Alice !", function_call=None)],
                prompt_tokens=120,
                candidates_tokens=15,
                thoughts_tokens=45,
            )

        captured_turn2_contents: list = []

        async def fake_stream_turn2(**kwargs):
            captured_turn2_contents.extend(kwargs["contents"])
            yield _make_chunk(
                [SimpleNamespace(thought=False, text="Suite OK", function_call=None)],
                prompt_tokens=180,
                candidates_tokens=10,
                thoughts_tokens=0,
            )

        turn_counter = 0

        async def fake_generate_stream(**kwargs):
            nonlocal turn_counter
            turn_counter += 1
            if turn_counter == 1:
                return fake_stream_turn1(**kwargs)
            return fake_stream_turn2(**kwargs)

        fake_client = MagicMock()
        fake_client.aio.models.generate_content_stream = AsyncMock(
            side_effect=fake_generate_stream
        )

        with (
            patch.object(self._google, "is_available", return_value=True),
            patch.object(self._google, "_client", fake_client),
        ):
            # --- TURN 1 (conversation_id=None) ---
            r1 = await self.client.post(
                "/chat/stream",
                json={
                    "model": "gemma-4-31b-it",
                    "messages": [{"role": "user", "content": "Salut !"}],
                },
                headers=self.alice_headers,
            )
            self.assertEqual(r1.status_code, 200)
            self.assertTrue(r1.headers["content-type"].startswith("text/event-stream"))

            events1 = _parse_sse_lines(r1.text)
            self.assertEqual(
                [ev_name for ev_name, _ in events1],
                ["thinking", "tool_call", "text", "text", "done"],
            )
            done1 = events1[-1][1]
            conv_id = done1["conversation_id"]
            self.assertIsNotNone(conv_id)
            self.assertIsNotNone(done1["user_message_id"])
            self.assertIsNotNone(done1["assistant_message_id"])
            self.assertEqual(done1["usage"]["input_tokens"], 120)
            self.assertEqual(done1["usage"]["output_tokens"], 15)
            self.assertEqual(done1["usage"]["thoughts_tokens"], 45)

            # Verify Markdown export includes <summary>thinking</summary> and <summary>tool calls</summary>
            r_exp = await self.client.get(
                "/db/conversations/export",
                params={"conversation_id": conv_id},
                headers=self.alice_headers,
            )
            self.assertEqual(r_exp.status_code, 200)
            self.assertIn("<summary>thinking</summary>\n\nThinking step 1...", r_exp.text)
            self.assertIn("<summary>tool calls</summary>", r_exp.text)
            self.assertIn("> Bonjour Alice !", r_exp.text)

            # --- TURN 2 (history_mode="full" reuses Turn 1 DB messages cleanly) ---
            r2 = await self.client.post(
                "/chat/stream",
                json={
                    "model": "gemma-4-31b-it",
                    "conversation_id": conv_id,
                    "history_mode": "full",
                    "messages": [{"role": "user", "content": "Et ensuite ?"}],
                },
                headers=self.alice_headers,
            )
            self.assertEqual(r2.status_code, 200)
            events2 = _parse_sse_lines(r2.text)
            self.assertEqual([ev_name for ev_name, _ in events2], ["text", "done"])
            # Ensure stored `thinking` part was stripped before sending back to Google SDK
            model_turn_parts = captured_turn2_contents[1]["parts"]
            self.assertTrue(all("type" not in p for p in model_turn_parts))

    async def test_03_mid_stream_provider_error_yields_error_event(self) -> None:
        async def failing_stream(**_kwargs):
            yield _make_chunk(
                [SimpleNamespace(thought=False, text="Début...", function_call=None)]
            )
            raise RuntimeError("Upstream quota exceeded")

        fake_client = MagicMock()
        fake_client.aio.models.generate_content_stream = AsyncMock(
            return_value=failing_stream()
        )

        with (
            patch.object(self._google, "is_available", return_value=True),
            patch.object(self._google, "_client", fake_client),
        ):
            r = await self.client.post(
                "/chat/stream",
                json={
                    "model": "gemma-4-31b-it",
                    "messages": [{"content": "Boom"}],
                },
                headers=self.alice_headers,
            )
            self.assertEqual(r.status_code, 200)
            events = _parse_sse_lines(r.text)
            self.assertEqual([name for name, _ in events], ["text", "error"])
            self.assertIn("Upstream quota exceeded", events[-1][1]["message"])


if __name__ == "__main__":
    unittest.main()
