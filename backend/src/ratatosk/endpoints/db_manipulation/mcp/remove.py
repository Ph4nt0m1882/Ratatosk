from fastapi import HTTPException

from ratatosk.db.models import MCPServer, User
from ratatosk.db.session import async_session_maker


async def remove_mcp_server(server_id: str, user: User) -> dict[str, str]:
    async with async_session_maker() as session:
        server = await session.get(MCPServer, server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")

        # Only the owner or an administrator can delete an MCP server
        if server.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        await session.delete(server)
        await session.commit()

    return {"status": "deleted", "id": server_id}
