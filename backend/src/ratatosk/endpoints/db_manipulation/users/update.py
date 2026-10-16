from fastapi import HTTPException, Response
from sqlalchemy import select

from ratatosk.core.security import PH
from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker

from .models import UserContent, UserUpdate


async def update_user(
    id: str,
    current_user: User,
    data: UserUpdate,
    response: Response,
) -> UserContent:
    clean_update = data.model_dump(exclude_unset=True)

    async with async_session_maker() as session:
        stmt = select(User).where(User.id == id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        elif user.id == current_user.id and (
            "is_active" in clean_update or "is_admin" in clean_update
        ):
            response.headers["X-Server-Notice"] = (
                "Cannot modify is_active or is_admin on your own account; ignored"
            )
            clean_update.pop("is_active", None)
            clean_update.pop("is_admin", None)

        for key, value in clean_update.items():
            if key == "password":
                key, value = "hashed_password", PH.hash(data.password)
            setattr(user, key, value)

        await session.commit()
        await session.refresh(user)

    return UserContent.model_validate(user)
