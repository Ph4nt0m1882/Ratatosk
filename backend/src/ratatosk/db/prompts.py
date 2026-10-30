from sqlalchemy import select

from ratatosk.db.models import SystemPrompt
from ratatosk.db.session import async_session_maker


async def get_final_system_prompts() -> str:
    async with async_session_maker() as session:
        stmt = (
            select(SystemPrompt.content)
            .where(SystemPrompt.is_active)
            .order_by(SystemPrompt.hierarchy)
        )

        results = (await session.execute(stmt)).scalars().all()

        return "\n\n".join(results)

