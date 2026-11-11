import shlex
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException

from .models import MCPTransport


@dataclass(slots=True)
class NormalizedMCPConfig:
    name: str
    transport: MCPTransport
    command_or_url: str
    args: list[str]
    env_or_headers: dict[str, str]
    is_active: bool


_HTTP_TRANSPORTS = {
    "http",
    "streamable-http",
    "streamable_http",
    "streamablehttp",
}


def _infer_transport(
    explicit_transport: str | None,
    has_url: bool,
    has_command: bool,
    target_value: str,
) -> MCPTransport:
    if explicit_transport:
        norm = explicit_transport.strip().lower()
        if norm == "stdio":
            return MCPTransport.STDIO
        if norm == "sse":
            return MCPTransport.SSE
        if norm in _HTTP_TRANSPORTS:
            return MCPTransport.HTTP

    if has_url or target_value.startswith(("http://", "https://")):
        parsed_path = urlparse(target_value).path.rstrip("/").lower()
        if parsed_path.endswith("/sse"):
            return MCPTransport.SSE
        return MCPTransport.HTTP

    if has_command:
        return MCPTransport.STDIO

    raise HTTPException(
        status_code=422,
        detail="Could not determine MCP transport: provide 'command_or_url', 'command', or 'url'.",
    )


def normalize_mcp_server_entry(
    name: str, raw: dict[str, Any]
) -> NormalizedMCPConfig:
    """Normalize a single MCP server definition from Ratatosk, Claude, Cursor, VS Code, Windsurf, or Cline."""
    clean_name = name.strip()[:100]
    if not clean_name:
        raise HTTPException(status_code=422, detail="MCP server name cannot be empty.")

    raw_url = (
        raw.get("url")
        or raw.get("serverUrl")
        or raw.get("httpUrl")
        or raw.get("endpoint")
    )
    raw_command = raw.get("command")
    raw_combined = raw.get("command_or_url")

    raw_args = raw.get("args")
    args: list[str] = (
        [str(a) for a in raw_args] if isinstance(raw_args, list) else []
    )

    if raw_combined:
        target = str(raw_combined).strip()
        has_url = target.startswith(("http://", "https://"))
        has_command = not has_url
    elif raw_url:
        target = str(raw_url).strip()
        has_url = True
        has_command = False
    elif raw_command:
        cmd_str = str(raw_command).strip()
        if not args and " " in cmd_str:
            parts = shlex.split(cmd_str)
            target = parts[0] if parts else cmd_str
            args = parts[1:]
        else:
            target = cmd_str
        has_url = False
        has_command = True
    else:
        raise HTTPException(
            status_code=422,
            detail=f"MCP server '{clean_name}' is missing 'command', 'url', or 'command_or_url'.",
        )

    if not target:
        raise HTTPException(
            status_code=422,
            detail=f"MCP server '{clean_name}' has an empty command or URL.",
        )

    explicit_type = raw.get("transport") or raw.get("type")
    transport = _infer_transport(
        str(explicit_type) if explicit_type else None,
        has_url=has_url,
        has_command=has_command,
        target_value=target,
    )

    # Merge env / headers / env_or_headers into a clean dict[str, str]
    env_or_headers: dict[str, str] = {}
    for key_field in ("env", "headers", "env_or_headers"):
        mapping = raw.get(key_field)
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                if v is not None:
                    env_or_headers[str(k)] = str(v)

    # Normalize active state across `is_active`, `disabled` (Cline/Cursor), and `enabled`
    if raw.get("is_active") is not None:
        is_active = bool(raw["is_active"])
    elif raw.get("disabled") is not None:
        is_active = not bool(raw["disabled"])
    elif raw.get("enabled") is not None:
        is_active = bool(raw["enabled"])
    else:
        is_active = True

    return NormalizedMCPConfig(
        name=clean_name,
        transport=transport,
        command_or_url=target,
        args=args,
        env_or_headers=env_or_headers,
        is_active=is_active,
    )


def parse_universal_mcp_config(
    payload: dict[str, Any],
) -> list[NormalizedMCPConfig]:
    """Parse any multi-server or single-server MCP configuration JSON."""
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=422, detail="Empty or invalid MCP configuration.")

    # 1. Claude Desktop / Cursor / Windsurf / Cline: {"mcpServers": {...}}
    if isinstance(payload.get("mcpServers"), dict):
        servers_map = payload["mcpServers"]
    # 2. VS Code / GitHub Copilot: {"servers": {...}} or {"mcp": {"servers": {...}}}
    elif isinstance(payload.get("servers"), dict):
        servers_map = payload["servers"]
    elif isinstance(payload.get("mcp"), dict) and isinstance(
        payload["mcp"].get("servers"), dict
    ):
        servers_map = payload["mcp"]["servers"]
    # 3. Single server object with explicit "name" field
    elif "name" in payload and any(
        k in payload
        for k in ("command", "url", "serverUrl", "httpUrl", "command_or_url")
    ):
        return [normalize_mcp_server_entry(str(payload["name"]), payload)]
    # 4. Direct map of {"<server_name>": {"command": ..., ...}}
    else:
        servers_map = payload

    if not servers_map:
        raise HTTPException(
            status_code=422, detail="No MCP servers found in configuration."
        )

    results: list[NormalizedMCPConfig] = []
    for srv_name, srv_cfg in servers_map.items():
        if not isinstance(srv_cfg, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid configuration block for MCP server '{srv_name}'.",
            )
        results.append(normalize_mcp_server_entry(str(srv_name), srv_cfg))

    return results
