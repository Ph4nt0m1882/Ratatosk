from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from ratatosk.core.security import get_current_admin, get_current_user
from ratatosk.db.models import User

from .add import add_new_user
from .get import get_user
from .list import requests_users
from .models import UserContent, UserCreate, UserRequest, UserUpdate
from .remove import remove_user
from .update import update_user

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/list", dependencies=[Depends(get_current_admin)])
async def list_users(
    only_active: bool = False,
    only_admin: bool = False,
) -> list[UserContent]:
    return await requests_users(only_active, only_admin)


@router.get("", dependencies=[Depends(get_current_admin)])
async def users(
    filter: Annotated[UserRequest, Query()],
) -> UserContent:
    return await get_user(filter)


@router.get("/me")
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserContent:
    return UserContent.model_validate(user)


@router.post("", dependencies=[Depends(get_current_admin)])
async def post_user(data: UserCreate) -> UserContent:
    return await add_new_user(data)


@router.patch("", dependencies=[Depends(get_current_admin)])
async def patch_user(
    id: str,
    user: Annotated[User, Depends(get_current_user)],
    data: UserUpdate,
    response: Response,
) -> UserContent:
    return await update_user(id, user, data, response)


@router.patch("/me")
async def patch_me(
    user: Annotated[User, Depends(get_current_user)],
    data: UserUpdate,
    response: Response,
) -> UserContent:
    return await update_user(user.id, user, data, response)


@router.delete("", dependencies=[Depends(get_current_admin)])
async def delete_user(id: str, user: Annotated[User, Depends(get_current_user)]):
    return await remove_user(id, user)
