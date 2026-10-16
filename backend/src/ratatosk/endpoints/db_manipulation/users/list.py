from sqlalchemy import select

from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker

from .models import UserContent


async def requests_users(
    only_active: bool = False,
    only_admin: bool = False,
) -> list[UserContent]:

    async with async_session_maker() as session:
        stmt = select(  # exclude the password hash
            User.id,
            User.username,
            User.email,
            User.is_active,
            User.is_admin,
            User.created_at,
        ).order_by(User.username)

        if only_active:
            stmt = stmt.where(User.is_active)
        if only_admin:
            stmt = stmt.where(User.is_admin)

        results = await session.execute(stmt)

    return [UserContent.model_validate(result) for result in results.mappings().all()]
