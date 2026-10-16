import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ratatosk.core.config import settings
from ratatosk.core.security import (
    PH,
    create_access_token,
    get_current_user,
    hash_token,
)
from ratatosk.db.models import User, UserSession
from ratatosk.db.session import get_db

from .models import RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
    remember_me: bool = False,
    device_name: str | None = None,
) -> TokenResponse:
    result = await session.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if user.hashed_password:
        try:
            PH.verify(user.hashed_password, form_data.password)
        except VerifyMismatchError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

    refresh_token: str | None = None
    if remember_me:
        refresh_token = secrets.token_urlsafe(32)
        session.add(
            UserSession(
                user_id=user.id,
                device_name=device_name,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        await session.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=refresh_token,
    )


@router.post("/renew")
async def renew_access_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> TokenResponse:
    """Sliding session: issues a fresh 15-min access token while the user is active."""
    return TokenResponse(access_token=create_access_token(current_user.id))


@router.post("/refresh")
async def refresh_device_session(
    data: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Fast-auth: validates and rotates the single-use 15-day device token."""
    result = await session.execute(
        select(UserSession).where(
            UserSession.token_hash == hash_token(data.refresh_token)
        )
    )
    user_session = result.scalar_one_or_none()

    user = await session.get(User, user_session.user_id) if user_session else None
    if (
        not user_session
        or not user
        or not user.is_active
        or user_session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC)
    ):
        if user_session:
            await session.delete(user_session)
            await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_refresh_token = secrets.token_urlsafe(32)
    user_session.token_hash = hash_token(new_refresh_token)
    user_session.expires_at = datetime.now(UTC) + timedelta(
        days=settings.refresh_token_expire_days
    )
    await session.commit()

    return TokenResponse(
        access_token=create_access_token(user_session.user_id),
        refresh_token=new_refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await session.execute(
        delete(UserSession).where(
            UserSession.token_hash == hash_token(data.refresh_token)
        )
    )
    await session.commit()
