from fastapi import Query
from pydantic import AwareDatetime, BaseModel, ConfigDict


class UserRequest(BaseModel):
    id: str | None = Query(default=None, description="Filter by id")
    username: str | None = Query(default=None, description="Filter by username")
    email: str | None = Query(
        default=None,
        description="Filter by email (Please note: providing an email address is optional.)",
    )


class UserBase(BaseModel):
    username: str
    email: str | None = None
    is_active: bool = True
    is_admin: bool = False


class UserCreate(UserBase):
    password: str | None = None


class UserContent(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: AwareDatetime


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = None
