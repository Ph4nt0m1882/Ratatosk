from fastapi import HTTPException
from sqlalchemy import select

from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker


async def remove_user(id: str, current_user: User):
    async with async_session_maker() as session:
        stmt = select(User).where(User.id == id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        elif user.id == current_user.id:
            raise HTTPException(
                status_code=404,
                detail="You cannot delete your own account; please ask another administrator.",
            )

        await session.delete(user)
        await session.commit()
