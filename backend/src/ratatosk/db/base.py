from typing import Any, Self

from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

from ratatosk.db.session import async_session_maker


class Base(DeclarativeBase):
    @classmethod
    async def get_by_id(
        cls, id: str, fields: list[str] | None = None
    ) -> dict[str, Any] | Self | None:
        async with async_session_maker() as session:
            if fields:
                cols = [getattr(cls, f) for f in fields]
                stmt = select(*cols).where(cls.id == id)
                row = (await session.execute(stmt)).mappings().one_or_none()
                return dict(row) if row else None
            return await session.get(cls, id)
