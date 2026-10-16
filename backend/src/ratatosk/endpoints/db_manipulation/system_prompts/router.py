from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from ratatosk.core.security import get_current_admin

from .add import add_new_system_prompts
from .get import get_system_prompts
from .list import requests_system_prompts
from .models import (
    SystemPromptContent,
    SystemPromptCreate,
    SystemPromptMetadata,
    SystemPromptRequest,
    SystemPromptUpdate,
)
from .remove import remove_system_prompts
from .reset import reset_all_system_prompt, reset_system_prompt
from .update import update_system_prompts

router = APIRouter(prefix="/system_prompts", tags=["System_Prompts"])


@router.get("/list")
async def list_system_prompts(
    only_active: bool = False,
) -> list[SystemPromptMetadata]:
    return await requests_system_prompts(only_active)


@router.get("")
async def system_prompt(
    filter: Annotated[SystemPromptRequest, Query()],
) -> SystemPromptContent:
    return await get_system_prompts(filter)


@router.post("", dependencies=[Depends(get_current_admin)])
async def post_system_prompt(data: SystemPromptCreate) -> SystemPromptContent:
    return await add_new_system_prompts(data)


@router.patch("", dependencies=[Depends(get_current_admin)])
async def patch_system_prompt(
    id: str,
    data: SystemPromptUpdate,
    response: Response,
) -> SystemPromptContent:
    return await update_system_prompts(id, data, response)


@router.delete("", status_code=204, dependencies=[Depends(get_current_admin)])
async def delete_system_prompts(id: str):
    return await remove_system_prompts(id)


@router.post("/reset", dependencies=[Depends(get_current_admin)])
async def post_reset_system_prompts(id: str) -> SystemPromptContent:
    return await reset_system_prompt(id)


@router.post("/reset/all", dependencies=[Depends(get_current_admin)])
async def post_reset_all_system_prompts() -> list[SystemPromptMetadata]:
    return await reset_all_system_prompt()
