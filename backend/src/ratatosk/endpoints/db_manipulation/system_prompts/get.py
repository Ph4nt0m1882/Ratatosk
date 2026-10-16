from fastapi import HTTPException
from sqlalchemy import select

from ratatosk.db.models import SystemPrompt
from ratatosk.db.session import async_session_maker

from .models import SystemPromptContent, SystemPromptRequest


async def get_system_prompts(filter: SystemPromptRequest) -> SystemPromptContent:
    async with async_session_maker() as session:
        stmt = select(SystemPrompt)

        if filter.id:
            stmt = stmt.where(SystemPrompt.id == filter.id)
        if filter.name:
            stmt = stmt.where(SystemPrompt.name == filter.name)
        if filter.hierarchy:
            stmt = stmt.where(SystemPrompt.hierarchy == filter.hierarchy)

        results = await session.execute(stmt)

    prompt = results.scalars().first()

    if not prompt:
        raise HTTPException(status_code=404, detail="System prompt not found")

    return SystemPromptContent.model_validate(prompt)


async def get_final_system_prompts() -> str:
    async with async_session_maker() as session:
        stmt = (
            select(SystemPrompt.content)
            .where(SystemPrompt.is_active)
            .order_by(SystemPrompt.hierarchy)
        )

        results = (await session.execute(stmt)).scalars().all()

        return "\n\n".join(results)
