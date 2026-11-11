from typing import Annotated

from fastapi import APIRouter, Depends

from ratatosk.core.security import get_current_user
from ratatosk.db.models import User

from .add import add_mcp_server, import_mcp_servers
from .list import list_mcp_servers
from .models import (
    MCPConfigImportRequest,
    MCPServerCreate,
    MCPServerData,
    MCPServerUpdate,
)
from .remove import remove_mcp_server
from .update import update_mcp_server

router = APIRouter(prefix="/mcp", tags=["MCP Servers"])


@router.get("/list")
async def list_mcp_servers_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    only_active: bool = False,
    all_users: bool = False,
    user_id: str | None = None,
) -> list[MCPServerData]:
    return await list_mcp_servers(
        user, only_active=only_active, all_users=all_users, user_id=user_id
    )


@router.post("")
async def create_mcp_server_endpoint(
    data: MCPServerCreate,
    user: Annotated[User, Depends(get_current_user)],
) -> MCPServerData:
    return await add_mcp_server(data, user)


@router.post("/import")
async def import_mcp_servers_endpoint(
    request: MCPConfigImportRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> list[MCPServerData]:
    return await import_mcp_servers(request, user)


@router.patch("")
async def patch_mcp_server_endpoint(
    server_id: str,
    data: MCPServerUpdate,
    user: Annotated[User, Depends(get_current_user)],
) -> MCPServerData:
    return await update_mcp_server(server_id, data, user)


@router.delete("")
async def delete_mcp_server_endpoint(
    server_id: str,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    return await remove_mcp_server(server_id, user)
