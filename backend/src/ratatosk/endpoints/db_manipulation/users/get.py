from fastapi import HTTPException
from sqlalchemy import select

from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker

from .models import UserContent, UserRequest


async def get_user(filter: UserRequest) -> UserContent:
    async with async_session_maker() as session:
        stmt = select(  # exclude the password hash
            User.id,
            User.username,
            User.email,
            User.is_active,
            User.is_admin,
            User.created_at,
        )

        if filter.id:
            stmt = stmt.where(User.id == filter.id)
        if filter.username:
            stmt = stmt.where(User.username == filter.username)
        if filter.email:
            stmt = stmt.where(User.email == filter.email)

        results = await session.execute(stmt)

    prompt = results.mappings().first()

    if not prompt:
        raise HTTPException(status_code=404, detail="User not found")

    return UserContent.model_validate(prompt)
