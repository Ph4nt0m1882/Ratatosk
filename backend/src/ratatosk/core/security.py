import base64
import hashlib
from typing import Annotated

from argon2 import PasswordHasher
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ratatosk.core.config import settings
from ratatosk.db.models import User
from ratatosk.db.session import get_db

PH = PasswordHasher()
FERNET = Fernet(
    base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    return FERNET.encrypt(user_id.encode()).decode()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        user_id = FERNET.decrypt(
            token.encode(),
            ttl=settings.access_token_expire_minutes * 60,
        ).decode()
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or non-existent user",
        )
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user
