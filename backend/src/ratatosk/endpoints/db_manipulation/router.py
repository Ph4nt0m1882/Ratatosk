from typing import Annotated

from fastapi import APIRouter, Query, Response

from .models import (
    SystemPromptContent,
    SystemPromptCreate,
    SystemPromptMetadata,
    SystemPromptRequest,
    SystemPromptUpdate,
)
from .system_prompts.add import add_new_system_prompts
from .system_prompts.get import get_system_prompts
from .system_prompts.list import requests_system_prompts
from .system_prompts.remove import remove_system_prompts
from .system_prompts.reset import reset_all_system_prompt, reset_system_prompt
from .system_prompts.update import update_system_prompts

router = APIRouter(
    prefix="/db",
    tags=["Database manipulation"],
)

## System prompts


@router.get("/system_prompts/list")
async def list_system_prompts(
    only_active: bool = False,
) -> list[SystemPromptMetadata]:
    return await requests_system_prompts(only_active)


@router.get("/system_prompts")
async def system_prompt(
    filter: Annotated[SystemPromptRequest, Query()],
) -> SystemPromptContent:
    return await get_system_prompts(filter)


@router.post("/system_prompts")
async def post_system_prompt(data: SystemPromptCreate) -> SystemPromptContent:
    return await add_new_system_prompts(data)


@router.patch("/system_prompts")
async def patch_system_prompt(
    id: str,
    data: SystemPromptUpdate,
    response: Response,
) -> SystemPromptContent:
    return await update_system_prompts(id, data, response)


@router.delete("/system_prompts", status_code=204)
async def delete_system_prompts(id: str):
    return await remove_system_prompts(id)


@router.post("/system_prompts/reset")
async def post_reset_system_prompts(id: str) -> SystemPromptContent:
    return await reset_system_prompt(id)


@router.post("/system_prompts/reset/all")
async def post_reset_all_system_prompts() -> list[SystemPromptMetadata]:
    return await reset_all_system_prompt()
