from ratatosk.db.models import SystemPrompt
from ratatosk.db.session import async_session_maker

from ..models import SystemPromptContent, SystemPromptCreate


async def add_new_system_prompts(data: SystemPromptCreate) -> SystemPromptContent:
    async with async_session_maker() as session:
        sys_prompt = SystemPrompt(**data.model_dump(), is_default=False)
        session.add(sys_prompt)
        await session.commit()
        await session.refresh(sys_prompt)

        return SystemPromptContent.model_validate(sys_prompt)
