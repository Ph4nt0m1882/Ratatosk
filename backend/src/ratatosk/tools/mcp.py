import asyncio
import base64
import os
import re
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx
from mcp import Client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import or_, select

from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import Attachment, MCPServer
from ratatosk.db.session import async_session_maker
from ratatosk.endpoints.db_manipulation.attachments.stats import ATTACHMENT_STATS_TASK
from ratatosk.file_manager import DestPaths, FileStorageManager
from ratatosk.tools.builtin import (
    GeneratedAttachmentInfo,
    ToolContext,
    ToolExecutionResult,
)


@dataclass(slots=True)
class MCPToolBinding:
    """Binds a namespaced LLM function name to its originating MCPServer and remote tool name."""

    full_name: str
    remote_tool_name: str
    server: MCPServer


def sanitize_mcp_name(name: str) -> str:
    """Normalize an MCP server or tool name into a safe identifier segment."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip()).strip("_").lower()
    return cleaned or "mcp"


def build_mcp_tool_name(server_name: str, tool_name: str) -> str:
    """Build a namespaced Google-compatible function name (`mcp__<server>__<tool>`)."""
    srv_slug = sanitize_mcp_name(server_name)[:24]
    tool_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", tool_name.strip()).strip("_") or "tool"
    combined = f"mcp__{srv_slug}__{tool_slug}"
    return combined[:64]


def clean_mcp_input_schema(raw_schema: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure an MCP tool's JSON schema is clean and valid for Google GenAI function declarations."""
    if not isinstance(raw_schema, dict):
        return {"type": "object", "properties": {}}

    cleaned: dict[str, Any] = {
        "type": raw_schema.get("type", "object"),
        "properties": raw_schema.get("properties", {}),
    }
    if "required" in raw_schema and isinstance(raw_schema["required"], list):
        cleaned["required"] = raw_schema["required"]
    if "description" in raw_schema and isinstance(raw_schema["description"], str):
        cleaned["description"] = raw_schema["description"]
    return cleaned


@asynccontextmanager
async def open_mcp_client(
    server: MCPServer,
    timeout_seconds: float = 15.0,
) -> AsyncIterator[Client]:
    """Open an MCP Client session over stdio, sse, or streamable HTTP."""
    transport_type = (server.transport or "stdio").lower().strip()

    async with AsyncExitStack() as stack:
        if transport_type == "stdio":
            merged_env = dict(os.environ)
            if server.env_or_headers:
                merged_env.update(
                    {str(k): str(v) for k, v in server.env_or_headers.items()}
                )
            params = StdioServerParameters(
                command=server.command_or_url,
                args=[str(a) for a in (server.args or [])],
                env=merged_env,
            )
            client = await stack.enter_async_context(
                Client(params, read_timeout_seconds=timeout_seconds)
            )
            yield client
        elif transport_type == "sse":
            headers = (
                {str(k): str(v) for k, v in server.env_or_headers.items()}
                if server.env_or_headers
                else None
            )
            transport = sse_client(
                server.command_or_url,
                headers=headers,
                timeout=timeout_seconds,
            )
            client = await stack.enter_async_context(
                Client(transport, read_timeout_seconds=timeout_seconds)
            )
            yield client
        elif transport_type in ("http", "streamable-http", "streamable_http"):
            headers = (
                {str(k): str(v) for k, v in server.env_or_headers.items()}
                if server.env_or_headers
                else None
            )
            http_client = await stack.enter_async_context(
                httpx.AsyncClient(headers=headers, timeout=timeout_seconds)
            )
            transport = streamable_http_client(
                server.command_or_url,
                http_client=http_client,
            )
            client = await stack.enter_async_context(
                Client(transport, read_timeout_seconds=timeout_seconds)
            )
            yield client
        else:
            raise ValueError(f"Unsupported MCP transport: {server.transport!r}")


async def get_active_mcp_servers(user_id: str | None) -> list[MCPServer]:
    """Fetch active global and user-specific MCP servers, letting user servers override global ones by slug."""
    async with async_session_maker() as session:
        if user_id:
            cond = or_(MCPServer.user_id.is_(None), MCPServer.user_id == user_id)
        else:
            cond = MCPServer.user_id.is_(None)

        stmt = (
            select(MCPServer)
            .where(MCPServer.is_active.is_(True), cond)
            .order_by(MCPServer.created_at.asc())
        )
        rows = (await session.execute(stmt)).scalars().all()

    by_slug: dict[str, MCPServer] = {}
    # Load global servers first, then allow user-specific servers with the same slug to override
    for srv in rows:
        if srv.user_id is None:
            by_slug[sanitize_mcp_name(srv.name)] = srv
    for srv in rows:
        if srv.user_id is not None:
            by_slug[sanitize_mcp_name(srv.name)] = srv

    return list(by_slug.values())


async def _discover_single_server_tools(
    server: MCPServer,
    timeout_seconds: float = 15.0,
) -> tuple[list[dict[str, Any]], dict[str, MCPToolBinding]]:
    declarations: list[dict[str, Any]] = []
    bindings: dict[str, MCPToolBinding] = {}
    try:
        async with open_mcp_client(server, timeout_seconds=timeout_seconds) as client:
            tools_res = await client.list_tools()
            for tool in tools_res.tools:
                full_name = build_mcp_tool_name(server.name, tool.name)
                desc = (tool.description or tool.title or tool.name).strip()
                declarations.append(
                    {
                        "name": full_name,
                        "description": f"[MCP: {server.name}] {desc}",
                        "parameters_json_schema": clean_mcp_input_schema(
                            tool.input_schema
                        ),
                    }
                )
                bindings[full_name] = MCPToolBinding(
                    full_name=full_name,
                    remote_tool_name=tool.name,
                    server=server,
                )
    except Exception:  # noqa: BLE001
        # A single offline/misconfigured MCP server must not break the chat turn
        return [], {}
    return declarations, bindings


async def discover_mcp_tools(
    user_id: str | None,
    timeout_seconds: float = 15.0,
) -> tuple[list[dict[str, Any]], dict[str, MCPToolBinding]]:
    """Discover tools from all active MCP servers for the user."""
    servers = await get_active_mcp_servers(user_id)
    if not servers:
        return [], {}

    results = await asyncio.gather(
        *(
            _discover_single_server_tools(srv, timeout_seconds=timeout_seconds)
            for srv in servers
        )
    )
    all_declarations: list[dict[str, Any]] = []
    all_bindings: dict[str, MCPToolBinding] = {}
    for decls, binds in results:
        all_declarations.extend(decls)
        all_bindings.update(binds)
    return all_declarations, all_bindings


async def _save_mcp_image_attachment(
    b64_data: str,
    mime_type: str,
    server_name: str,
    user_id: str | None,
    index: int,
) -> GeneratedAttachmentInfo | None:
    try:
        raw_bytes = base64.b64decode(b64_data)
    except (ValueError, TypeError):
        return None

    storage = FileStorageManager()
    tool_tag = f"mcp_{sanitize_mcp_name(server_name)}"
    file_hash, rel_path, file_size = await asyncio.to_thread(
        storage.save_file,
        DestPaths.TOOLS,
        raw_bytes,
        tool_name=tool_tag,
    )
    width, height = await asyncio.to_thread(storage.get_image_dimensions, rel_path)
    source_tag = f"mcp:{server_name}"

    async with async_session_maker() as session:
        existing = (
            await session.execute(
                select(Attachment).where(
                    Attachment.user_id == user_id,
                    Attachment.source == source_tag,
                    Attachment.file_hash == file_hash,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.expires_at = None
            await session.commit()
            await session.refresh(existing)
            att = existing
        else:
            att = Attachment(
                user_id=user_id,
                source=source_tag,
                file_hash=file_hash,
                mime_type=mime_type or "image/png",
                file_path=rel_path,
                file_size=file_size,
                width=width,
                height=height,
                is_generated=False,
                expires_at=None,
            )
            session.add(att)
            await session.commit()
            await session.refresh(att)

    idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)
    ext = (
        mime_type.split("/", 1)[-1].split("+", 1)[0]
        if "/" in (mime_type or "")
        else "png"
    )
    return GeneratedAttachmentInfo(
        id=att.id,
        filename=f"{tool_tag}_{index}.{ext}",
        mime_type=att.mime_type,
        is_generated=False,
        external_uri=None,
    )


async def execute_mcp_tool(
    binding: MCPToolBinding,
    args: dict[str, Any] | None,
    ctx: ToolContext,
    timeout_seconds: float = 30.0,
) -> ToolExecutionResult:
    """Execute a tool call on its remote MCP server and normalize the result."""
    try:
        async with open_mcp_client(
            binding.server, timeout_seconds=timeout_seconds
        ) as client:
            call_res = await client.call_tool(
                binding.remote_tool_name,
                dict(args or {}),
            )
    except Exception as exc:  # noqa: BLE001
        return ToolExecutionResult(
            output={
                "error": f"MCP server '{binding.server.name}' error: {exc}",
                "is_error": True,
            }
        )

    texts: list[str] = []
    attachments: list[GeneratedAttachmentInfo] = []
    img_idx = 0

    for item in getattr(call_res, "content", None) or []:
        item_type = getattr(item, "type", None)
        if item_type == "text" and getattr(item, "text", None) is not None:
            texts.append(str(item.text))
        elif item_type == "image" and getattr(item, "data", None):
            img_idx += 1
            att_info = await _save_mcp_image_attachment(
                b64_data=str(item.data),
                mime_type=str(getattr(item, "mime_type", "image/png")),
                server_name=binding.server.name,
                user_id=ctx.user_id,
                index=img_idx,
            )
            if att_info is not None:
                attachments.append(att_info)

    output: dict[str, Any] = {
        "server": binding.server.name,
        "tool": binding.remote_tool_name,
        "is_error": bool(getattr(call_res, "is_error", False)),
    }
    structured = getattr(call_res, "structured_content", None)
    if structured is not None:
        output["structured_content"] = structured
    if texts:
        output["content"] = "\n".join(texts) if len(texts) > 1 else texts[0]

    return ToolExecutionResult(output=output, attachments=attachments)
