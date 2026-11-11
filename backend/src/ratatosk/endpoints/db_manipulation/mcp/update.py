from fastapi import HTTPException

from ratatosk.db.models import MCPServer, User
from ratatosk.db.session import async_session_maker

from .add import to_mcp_server_data
from .models import MCPServerData, MCPServerUpdate


async def update_mcp_server(
    server_id: str, data: MCPServerUpdate, user: User
) -> MCPServerData:
    clean_update = data.model_dump(exclude_none=True)

    async with async_session_maker() as session:
        server = await session.get(MCPServer, server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")

        if server.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        for key, value in clean_update.items():
            if key == "transport" and hasattr(value, "value"):
                setattr(server, key, value.value)
            else:
                setattr(server, key, value)

        await session.commit()
        await session.refresh(server)
        return to_mcp_server_data(server)
