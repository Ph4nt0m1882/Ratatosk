from fastapi import APIRouter, Depends

from ratatosk.core.security import get_current_user

from .system_prompts.router import router as system_prompts_router
from .users.router import router as users_router

router = APIRouter(
    prefix="/db",
    tags=["Database manipulation"],
    dependencies=[Depends(get_current_user)],
)

router.include_router(system_prompts_router)
router.include_router(users_router)
