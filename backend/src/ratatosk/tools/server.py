import asyncio
import os
import sys
from typing import Any, Literal

from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker
from ratatosk.endpoints.db_manipulation.conversations.list import requests_conversations
from ratatosk.endpoints.db_manipulation.conversations.models import ConversationUpdate
from ratatosk.endpoints.db_manipulation.conversations.remove import remove_conversation
from ratatosk.endpoints.db_manipulation.conversations.update import update_conversation

from .builtin import ToolContext, ToolVisibility, builtin_tool


def _trigger_process_restart() -> None:
    """Replace the current server process image to restart the backend cleanly."""
    os.execv(sys.executable, [sys.executable, *sys.argv])


@builtin_tool(visibility=ToolVisibility.KORNAK, admin_only=True)
async def reset_server(
    reason: str = "admin_request",
    delay_seconds: float = 1.0,
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    """Restart the Ratatosk backend server after a short grace period (Admin only)."""
    if ctx is None or not ctx.is_admin:
        return {"error": "Permission denied: admin privileges required"}

    clamped_delay = max(0.1, min(float(delay_seconds), 30.0))
    loop = asyncio.get_running_loop()
    loop.call_later(clamped_delay, _trigger_process_restart)

    return {
        "status": "restarting",
        "delay_seconds": clamped_delay,
        "reason": reason,
    }


@builtin_tool(visibility=ToolVisibility.ACTIVE, admin_only=False)
async def manage_conversation(
    action: Literal["list", "rename", "archive", "unarchive", "delete"],
    conversation_id: str = "",
    title: str = "",
    only_not_archived: bool = True,
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    """List, rename, archive, unarchive, or delete the user's conversations."""
    if ctx is None or not ctx.user_id:
        return {"error": "Authentication required"}

    async with async_session_maker() as session:
        user = await session.get(User, ctx.user_id)
        if user is None or not user.is_active:
            return {"error": "User not found or inactive"}

    if action == "list":
        convs = await requests_conversations(
            user=user, user_id=user.id, only_not_archived=only_not_archived
        )
        return {
            "status": "ok",
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "archived": c.archived,
                    "nb_message": c.nb_message,
                }
                for c in convs
            ],
        }

    target_id = conversation_id.strip() or (ctx.conversation_id or "")
    if not target_id:
        return {"error": "conversation_id is required for this action"}

    if action == "rename":
        clean_title = title.strip()
        if not clean_title:
            return {"error": "title is required when action is 'rename'"}
        mgr = await update_conversation(
            target_id,
            ConversationUpdate(title=clean_title, title_auto=False),
            user,
        )
        return {
            "status": "renamed",
            "conversation_id": mgr.id,
            "title": mgr.title,
        }

    if action in ("archive", "unarchive"):
        archived_state = action == "archive"
        mgr = await update_conversation(
            target_id,
            ConversationUpdate(archived=archived_state),
            user,
        )
        return {
            "status": "archived" if archived_state else "unarchived",
            "conversation_id": mgr.id,
            "archived": mgr.archived,
        }

    if action == "delete":
        await remove_conversation(target_id, user)
        return {
            "status": "deleted",
            "conversation_id": target_id,
        }

    return {"error": f"Unsupported action '{action}'"}
