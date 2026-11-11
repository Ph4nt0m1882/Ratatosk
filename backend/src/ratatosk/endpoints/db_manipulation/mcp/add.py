from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ratatosk.db.models import MCPServer, User
from ratatosk.db.session import async_session_maker

from .models import (
    MCPConfigImportRequest,
    MCPServerCreate,
    MCPServerData,
    MCPTransport,
)
from .parser import (
    NormalizedMCPConfig,
    normalize_mcp_server_entry,
    parse_universal_mcp_config,
)


def to_mcp_server_data(server: MCPServer) -> MCPServerData:
    return MCPServerData(
        id=server.id,
        name=server.name,
        transport=MCPTransport(server.transport),
        command_or_url=server.command_or_url,
        args=list(server.args or []),
        env_or_headers=dict(server.env_or_headers or {}),
        is_active=server.is_active,
        is_global=server.user_id is None,
        user_id=server.user_id,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


async def _upsert_normalized_mcp(
    session: AsyncSession,
    cfg: NormalizedMCPConfig,
    owner_user_id: str | None,
    *,
    overwrite_existing: bool,
) -> MCPServer:
    cond = (
        MCPServer.user_id.is_(None)
        if owner_user_id is None
        else (MCPServer.user_id == owner_user_id)
    )
    existing = (
        await session.execute(
            select(MCPServer).where(cond, MCPServer.name == cfg.name)
        )
    ).scalar_one_or_none()

    if existing is not None:
        if not overwrite_existing:
            raise HTTPException(
                status_code=409,
                detail=f"MCP server '{cfg.name}' already exists.",
            )
        existing.transport = cfg.transport.value
        existing.command_or_url = cfg.command_or_url
        existing.args = cfg.args
        existing.env_or_headers = cfg.env_or_headers
        existing.is_active = cfg.is_active
        await session.flush()
        return existing

    server = MCPServer(
        name=cfg.name,
        transport=cfg.transport.value,
        command_or_url=cfg.command_or_url,
        args=cfg.args,
        env_or_headers=cfg.env_or_headers,
        is_active=cfg.is_active,
        user_id=owner_user_id,
    )
    session.add(server)
    await session.flush()
    return server


async def add_mcp_server(data: MCPServerCreate, user: User) -> MCPServerData:
    if data.is_global and not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can create global MCP servers.",
        )

    owner_id = None if data.is_global else user.id
    normalized = normalize_mcp_server_entry(
        data.name, data.model_dump(exclude_none=True)
    )

    async with async_session_maker() as session:
        server = await _upsert_normalized_mcp(
            session, normalized, owner_id, overwrite_existing=False
        )
        await session.commit()
        await session.refresh(server)
        return to_mcp_server_data(server)


async def import_mcp_servers(
    request: MCPConfigImportRequest, user: User
) -> list[MCPServerData]:
    if request.is_global and not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can import global MCP servers.",
        )

    owner_id = None if request.is_global else user.id
    parsed_configs = parse_universal_mcp_config(request.config)

    saved: list[MCPServer] = []
    async with async_session_maker() as session:
        for cfg in parsed_configs:
            srv = await _upsert_normalized_mcp(
                session,
                cfg,
                owner_id,
                overwrite_existing=request.overwrite_existing,
            )
            saved.append(srv)
        await session.commit()
        for srv in saved:
            await session.refresh(srv)

    return [to_mcp_server_data(s) for s in saved]
