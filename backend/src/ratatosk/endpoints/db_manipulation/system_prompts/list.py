from sqlalchemy import select

from ratatosk.db.models import SystemPrompt
from ratatosk.db.session import async_session_maker

from .models import SystemPromptMetadata


async def requests_system_prompts(
    only_active: bool = False,
) -> list[SystemPromptMetadata]:

    async with async_session_maker() as session:
        stmt = select(
            SystemPrompt.id,
            SystemPrompt.name,
            SystemPrompt.hierarchy,
            SystemPrompt.description,
            SystemPrompt.is_active,
            SystemPrompt.is_default,
            SystemPrompt.updated_at.label("last_modification"),
        ).order_by(SystemPrompt.hierarchy)

        if only_active:
            stmt = stmt.where(SystemPrompt.is_active)

        results = await session.execute(stmt)

    return [
        SystemPromptMetadata.model_validate(result)
        for result in results.mappings().all()
    ]
