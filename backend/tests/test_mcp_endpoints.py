import unittest
from types import SimpleNamespace
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from ratatosk.app import app
from ratatosk.core.security import create_access_token
from ratatosk.db.base import Base
from ratatosk.db.models import MCPServer, User
from ratatosk.db.session import async_session_maker, engine
from ratatosk.providers.google.provider import GoogleProvider
from ratatosk.providers.provider import NoSearchMode
from ratatosk.providers.schemas import (
    DoneEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from ratatosk.tools import ToolContext, discover_mcp_tools, execute_mcp_tool


class TestMCPEndpointsSuite(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.alice = User(username="__ut_mcp_alice__", is_active=True, is_admin=False)
        self.bob = User(username="__ut_mcp_bob__", is_active=True, is_admin=False)
        self.admin = User(username="__ut_mcp_admin__", is_active=True, is_admin=True)

        async with async_session_maker() as session:
            await session.execute(
                delete(MCPServer).where(
                    MCPServer.name.in_(
                        [
                            "filesystem",
                            "sqlite-cline",
                            "windsurf-sse",
                            "vscode-http",
                            "global-search",
                            "alice-private",
                            "docker-math",
                        ]
                    )
                )
            )
            await session.execute(
                delete(User).where(
                    User.username.in_(
                        ["__ut_mcp_alice__", "__ut_mcp_bob__", "__ut_mcp_admin__"]
                    )
                )
            )
            session.add_all([self.alice, self.bob, self.admin])
            await session.commit()
            for u in (self.alice, self.bob, self.admin):
                await session.refresh(u)

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
        uids = [self.alice.id, self.bob.id, self.admin.id]
        async with async_session_maker() as session:
            await session.execute(
                delete(MCPServer).where(
                    MCPServer.user_id.in_(uids)
                    | (MCPServer.name == "global-search")
                )
            )
            await session.execute(delete(User).where(User.id.in_(uids)))
            await session.commit()
        await engine.dispose()

    async def test_01_universal_config_import_claude_cursor_windsurf_cline_vscode(
        self,
    ) -> None:
        # 1. Import Claude Desktop / Cursor / Windsurf / Cline formats in a single `mcpServers` block
        claude_cursor_payload = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
                    "env": {"NODE_ENV": "production"},
                },
                "sqlite-cline": {
                    "command": "uvx mcp-server-sqlite --db-path /tmp/app.db",
                    "disabled": True,
                },
                "windsurf-sse": {
                    "serverUrl": "https://mcp.example.org/v1/sse",
                    "headers": {"Authorization": "Bearer secret_token"},
                },
            }
        }
        r1 = await self.client.post(
            "/db/mcp/import",
            headers=self.alice_headers,
            json={"config": claude_cursor_payload},
        )
        self.assertEqual(r1.status_code, 200, r1.text)
        imported = {s["name"]: s for s in r1.json()}

        fs = imported["filesystem"]
        self.assertEqual(fs["transport"], "stdio")
        self.assertEqual(fs["command_or_url"], "npx")
        self.assertEqual(
            fs["args"], ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
        )
        self.assertEqual(fs["env_or_headers"], {"NODE_ENV": "production"})
        self.assertTrue(fs["is_active"])
        self.assertFalse(fs["is_global"])

        cline = imported["sqlite-cline"]
        self.assertEqual(cline["transport"], "stdio")
        self.assertEqual(cline["command_or_url"], "uvx")
        self.assertEqual(
            cline["args"], ["mcp-server-sqlite", "--db-path", "/tmp/app.db"]
        )
        self.assertFalse(cline["is_active"])

        ws = imported["windsurf-sse"]
        self.assertEqual(ws["transport"], "sse")
        self.assertEqual(ws["command_or_url"], "https://mcp.example.org/v1/sse")
        self.assertEqual(
            ws["env_or_headers"], {"Authorization": "Bearer secret_token"}
        )

        # 2. Import VS Code / GitHub Copilot `.vscode/mcp.json` format (`servers` + `streamable-http`)
        vscode_payload = {
            "servers": {
                "vscode-http": {
                    "type": "streamable-http",
                    "url": "https://mcp.example.org/api",
                    "headers": {"X-Api-Key": "12345"},
                }
            }
        }
        r2 = await self.client.post(
            "/db/mcp/import",
            headers=self.alice_headers,
            json={"config": vscode_payload},
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        vs_srv = r2.json()[0]
        self.assertEqual(vs_srv["name"], "vscode-http")
        self.assertEqual(vs_srv["transport"], "http")
        self.assertEqual(vs_srv["command_or_url"], "https://mcp.example.org/api")
        self.assertEqual(vs_srv["env_or_headers"], {"X-Api-Key": "12345"})

    async def test_02_permissions_global_vs_user_and_admin_override(self) -> None:
        # 1. Regular user (Alice) CANNOT create a global MCP server -> 403
        r_forbid_global = await self.client.post(
            "/db/mcp",
            headers=self.alice_headers,
            json={
                "name": "global-search",
                "command": "npx -y @mcp/search",
                "is_global": True,
            },
        )
        self.assertEqual(r_forbid_global.status_code, 403)

        # 2. Admin creates a global MCP server -> 200 (`is_global=True`, `user_id=None`)
        r_global = await self.client.post(
            "/db/mcp",
            headers=self.admin_headers,
            json={
                "name": "global-search",
                "command": "npx -y @mcp/search",
                "is_global": True,
            },
        )
        self.assertEqual(r_global.status_code, 200, r_global.text)
        global_srv = r_global.json()
        self.assertTrue(global_srv["is_global"])
        self.assertIsNone(global_srv["user_id"])

        # 3. Alice creates her own private MCP server
        r_alice = await self.client.post(
            "/db/mcp",
            headers=self.alice_headers,
            json={
                "name": "alice-private",
                "url": "https://alice.example.org/sse",
            },
        )
        self.assertEqual(r_alice.status_code, 200)
        alice_srv = r_alice.json()
        self.assertFalse(alice_srv["is_global"])
        self.assertEqual(alice_srv["user_id"], self.alice.id)

        # 4. Bob lists MCP servers -> sees `global-search`, does NOT see `alice-private`
        r_bob_list = await self.client.get("/db/mcp/list", headers=self.bob_headers)
        self.assertEqual(r_bob_list.status_code, 200)
        bob_names = [s["name"] for s in r_bob_list.json()]
        self.assertIn("global-search", bob_names)
        self.assertNotIn("alice-private", bob_names)

        # 5. Alice cannot delete `global-search` (403), Bob cannot delete `alice-private` (403)
        r_alice_del_global = await self.client.delete(
            "/db/mcp",
            params={"server_id": global_srv["id"]},
            headers=self.alice_headers,
        )
        self.assertEqual(r_alice_del_global.status_code, 403)

        r_bob_del_alice = await self.client.delete(
            "/db/mcp",
            params={"server_id": alice_srv["id"]},
            headers=self.bob_headers,
        )
        self.assertEqual(r_bob_del_alice.status_code, 403)

        # 6. Admin can list all users' servers (`all_users=True`) and delete Alice's server!
        r_admin_all = await self.client.get(
            "/db/mcp/list",
            params={"all_users": "true"},
            headers=self.admin_headers,
        )
        self.assertEqual(r_admin_all.status_code, 200)
        self.assertIn("alice-private", [s["name"] for s in r_admin_all.json()])

        r_admin_del_alice = await self.client.delete(
            "/db/mcp",
            params={"server_id": alice_srv["id"]},
            headers=self.admin_headers,
        )
        self.assertEqual(r_admin_del_alice.status_code, 200)

    async def test_03_docker_mcp_container_discovery_execution_and_chat_stream(
        self,
    ) -> None:
        # 1. Import our real Docker MCP server using standard Claude/Cursor JSON config
        docker_mcp_config = {
            "mcpServers": {
                "docker-math": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        "MCP_TEST_TAG=from_docker_env",
                        "ratatosk-mcp-test:latest",
                    ],
                }
            }
        }
        r_import = await self.client.post(
            "/db/mcp/import",
            headers=self.alice_headers,
            json={"config": docker_mcp_config},
        )
        self.assertEqual(r_import.status_code, 200, r_import.text)

        # 2. Discover tools from the live Docker MCP container
        declarations, bindings = await discover_mcp_tools(self.alice.id)
        decl_names = [d["name"] for d in declarations]
        self.assertIn("mcp__docker_math__calculate_fibonacci", decl_names)
        self.assertIn("mcp__docker_math__get_container_info", decl_names)

        # 3. Execute tools directly against the Docker container
        ctx = ToolContext(user_id=self.alice.id, is_admin=False)
        fib_res = await execute_mcp_tool(
            bindings["mcp__docker_math__calculate_fibonacci"],
            {"n": 10},
            ctx,
        )
        self.assertFalse(fib_res.output["is_error"], fib_res.output)
        self.assertIn("55", str(fib_res.output))

        info_res = await execute_mcp_tool(
            bindings["mcp__docker_math__get_container_info"],
            {"label": "docker-check"},
            ctx,
        )
        self.assertFalse(info_res.output["is_error"], info_res.output)
        self.assertIn("from_docker_env", str(info_res.output))

        # 4. Verify end-to-end execution through GoogleProvider.chat_stream
        call_round = 0

        async def fake_generate_content_stream(*, model, contents, config):
            nonlocal call_round
            call_round += 1
            if call_round == 1:
                fn_decls = []
                for t in config.get("tools", []):
                    if "function_declarations" in t:
                        fn_decls.extend(d["name"] for d in t["function_declarations"])
                self.assertIn("mcp__docker_math__calculate_fibonacci", fn_decls)

                async def _round1():
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
                                                id="call_mcp_1",
                                                name="mcp__docker_math__calculate_fibonacci",
                                                args={"n": 12},
                                            ),
                                        )
                                    ]
                                ),
                                grounding_metadata=None,
                            )
                        ],
                        usage_metadata=SimpleNamespace(
                            prompt_token_count=10,
                            candidates_token_count=5,
                            thoughts_token_count=0,
                        ),
                    )

                return _round1()

            async def _round2():
                yield SimpleNamespace(
                    model_version=model,
                    candidates=[
                        SimpleNamespace(
                            content=SimpleNamespace(
                                parts=[
                                    SimpleNamespace(
                                        thought=False,
                                        text="Fibonacci(12) from Docker MCP is 144.",
                                        function_call=None,
                                    )
                                ]
                            ),
                            grounding_metadata=None,
                        )
                    ],
                    usage_metadata=SimpleNamespace(
                        prompt_token_count=15,
                        candidates_token_count=8,
                        thoughts_token_count=0,
                    ),
                )

            return _round2()

        provider = GoogleProvider.__new__(GoogleProvider)
        provider.provider_id = "google"
        provider.display_name = "Gemini"
        provider._client = SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(
                    generate_content_stream=fake_generate_content_stream
                )
            )
        )

        with patch.object(provider, "is_available", return_value=True), patch.object(
            provider, "list_models", return_value={}
        ):
            events = [
                ev
                async for ev in provider.chat_stream(
                    model="gemini-2.5-flash",
                    messages=[{"role": "user", "content": "Compute Fib(12) via Docker MCP"}],
                    user_id=self.alice.id,
                    search_mode=NoSearchMode(),
                )
            ]

        tool_calls = [e for e in events if isinstance(e, ToolCallEvent)]
        tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
        text_events = [e for e in events if isinstance(e, TextEvent)]
        done_events = [e for e in events if isinstance(e, DoneEvent)]

        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].name, "mcp__docker_math__calculate_fibonacci")
        self.assertEqual(len(tool_results), 1)
        self.assertIn("144", str(tool_results[0].result))
        self.assertEqual(len(text_events), 1)
        self.assertEqual(len(done_events), 1)


if __name__ == "__main__":
    unittest.main()
