from fastapi import APIRouter, Depends

from ratatosk.core.security import get_current_user

from .attachments.router import router as attachments_router
from .conversations.router import router as conversation_router
from .mcp.router import router as mcp_router
from .system_prompts.router import router as system_prompts_router
from .users.router import router as users_router

router = APIRouter(
    prefix="/db",
    tags=["Database manipulation"],
    dependencies=[Depends(get_current_user)],
)

router.include_router(attachments_router)
router.include_router(conversation_router)
router.include_router(mcp_router)
router.include_router(system_prompts_router)
router.include_router(users_router)
