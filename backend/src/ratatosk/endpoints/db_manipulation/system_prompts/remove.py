from fastapi import HTTPException
from ratatosk.db.models import SystemPrompt
from ratatosk.db.session import async_session_maker
from sqlalchemy import select


async def remove_system_prompts(id: str):
    async with async_session_maker() as session:
        stmt = select(SystemPrompt).where(SystemPrompt.id == id)
        sys_prompt = (await session.execute(stmt)).scalar_one_or_none()

        if sys_prompt is None:
            raise HTTPException(status_code=404, detail="System prompt not found")

        await session.delete(sys_prompt)
        await session.commit()
