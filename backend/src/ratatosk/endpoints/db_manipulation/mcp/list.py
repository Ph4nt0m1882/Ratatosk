from fastapi import HTTPException
from sqlalchemy import or_, select

from ratatosk.db.models import MCPServer, User
from ratatosk.db.session import async_session_maker

from .add import to_mcp_server_data
from .models import MCPServerData


async def list_mcp_servers(
    user: User,
    *,
    only_active: bool = False,
    all_users: bool = False,
    user_id: str | None = None,
) -> list[MCPServerData]:
    if (all_users or (user_id is not None and user_id != user.id)) and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    async with async_session_maker() as session:
        stmt = select(MCPServer)

        if not (all_users and user.is_admin):
            target_uid = user_id or user.id
            stmt = stmt.where(
                or_(MCPServer.user_id == target_uid, MCPServer.user_id.is_(None))
            )
        elif user_id is not None:
            stmt = stmt.where(MCPServer.user_id == user_id)

        if only_active:
            stmt = stmt.where(MCPServer.is_active.is_(True))

        stmt = stmt.order_by(MCPServer.created_at.asc(), MCPServer.name.asc())
        rows = (await session.execute(stmt)).scalars().all()

    return [to_mcp_server_data(row) for row in rows]
