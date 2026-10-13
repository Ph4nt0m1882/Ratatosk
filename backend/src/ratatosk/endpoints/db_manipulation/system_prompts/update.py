from fastapi import HTTPException, Response
from ratatosk.db.models import SystemPrompt
from ratatosk.db.session import async_session_maker
from sqlalchemy import select

from ..models import SystemPromptContent, SystemPromptUpdate


async def update_system_prompts(
    id: str,
    data: SystemPromptUpdate,
    response: Response,
) -> SystemPromptContent:
    clean_update = data.model_dump(exclude_unset=True)

    async with async_session_maker() as session:
        stmt = select(SystemPrompt).where(SystemPrompt.id == id)
        sys_prompt = (await session.execute(stmt)).scalar_one_or_none()

        if sys_prompt is None:
            raise HTTPException(status_code=404, detail="System prompt not found")

        if sys_prompt.is_default and "name" in clean_update:
            response.headers["X-Server-Notice"] = (
                "Modifying the name of a default prompt is prohibited; name modification ignored"
            )
            clean_update.pop("name")  # dont permit to rename a default sys prompt

        if sys_prompt is None:
            raise HTTPException(status_code=404, detail="System prompt not found")

        for key, value in clean_update.items():
            setattr(sys_prompt, key, value)

        await session.commit()
        await session.refresh(sys_prompt)

    return SystemPromptContent.model_validate(sys_prompt)
