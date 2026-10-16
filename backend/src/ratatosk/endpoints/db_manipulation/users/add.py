from ratatosk.core.security import PH
from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker

from .models import UserContent, UserCreate


async def add_new_user(data: UserCreate) -> UserContent:
    async with async_session_maker() as session:
        dump = data.model_dump(exclude={"password"})
        if data.password:
            dump["hashed_password"] = PH.hash(data.password)

        user = User(**dump)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return UserContent.model_validate(user)
