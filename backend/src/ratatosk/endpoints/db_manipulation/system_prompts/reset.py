from fastapi import HTTPException
from sqlalchemy import delete, select

from ratatosk.db.models import SystemPrompt
from ratatosk.db.seeds import get_default_prompts
from ratatosk.db.session import async_session_maker

from .list import requests_system_prompts
from .models import SystemPromptContent, SystemPromptMetadata


async def reset_system_prompt(id: str) -> SystemPromptContent:
    async with async_session_maker() as session:
        stmt = select(SystemPrompt).where(SystemPrompt.id == id)
        sys_prompt = (await session.execute(stmt)).scalar_one_or_none()

        if sys_prompt is None:
            raise HTTPException(status_code=404, detail="System prompt not found")

        prompts = get_default_prompts()
        prompt = None

        prompt = next((sp for sp in prompts if sp.name == sys_prompt.name), None)

        if prompt is None:
            raise HTTPException(
                status_code=404,
                detail="Cannot correlate a default system prompt with this file, make sure that the name not change",
            )

        FIELDS_TO_RESET = ["content", "description", "hierarchy", "is_active"]

        for field in FIELDS_TO_RESET:
            setattr(sys_prompt, field, getattr(prompt, field))

        await session.commit()
        await session.refresh(sys_prompt)

        return SystemPromptContent.model_validate(sys_prompt)


async def reset_all_system_prompt() -> list[SystemPromptMetadata]:
    async with async_session_maker() as session:
        await session.execute(delete(SystemPrompt))
        session.add_all(get_default_prompts())
        await session.commit()

    return await requests_system_prompts()
