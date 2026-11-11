from enum import StrEnum
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field


class MCPTransport(StrEnum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class MCPServerData(BaseModel):
    id: str
    name: str
    transport: MCPTransport
    command_or_url: str
    args: list[str] = Field(default_factory=list)
    env_or_headers: dict[str, str] = Field(default_factory=dict)
    is_active: bool
    is_global: bool
    user_id: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class MCPServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    transport: str | None = None
    command_or_url: str | None = None
    args: list[str] | None = None
    env_or_headers: dict[str, str] | None = None
    is_active: bool | None = None
    is_global: bool = False

    # Compatibility fields for direct single-server Claude / Cursor / VS Code / Windsurf dicts
    type: str | None = None
    command: str | None = None
    url: str | None = None
    serverUrl: str | None = None
    httpUrl: str | None = None
    env: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    disabled: bool | None = None
    enabled: bool | None = None


class MCPServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    transport: MCPTransport | None = None
    command_or_url: str | None = None
    args: list[str] | None = None
    env_or_headers: dict[str, str] | None = None
    is_active: bool | None = None


class MCPConfigImportRequest(BaseModel):
    """Accepts any universal MCP config JSON (Claude Desktop, Cursor, VS Code, Windsurf, Cline)."""

    config: dict[str, Any]
    is_global: bool = False
    overwrite_existing: bool = True
