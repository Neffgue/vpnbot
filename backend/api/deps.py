import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.utils.security import decode_token
from backend.repositories.user_repo import UserRepository
from backend.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Static admin API key — used by the Telegram bot to call admin endpoints
_ADMIN_API_KEY = settings.API_KEY


class _MockAdminUser:
    """Lightweight mock object representing a bot-authenticated admin."""
    id = "bot-admin"
    telegram_id = 0
    username = "bot_admin"
    first_name = "Bot"
    is_admin = True
    is_banned = False
    balance = 0.0
    referral_code = ""
    free_trial_used = False


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
):
    """
    Get current authenticated user from JWT token.
    Token should be passed as Authorization header: Bearer <token>
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is banned",
        )

    return user


async def get_admin_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
):
    """
    Verify admin access.
    Accepts either:
    1. A static API key (set via API_KEY env var) — used by the Telegram bot.
    2. A valid JWT token for a user with is_admin=True — used by the web admin panel.
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check static API key first (bot admin access)
    if _ADMIN_API_KEY and token == _ADMIN_API_KEY:
        return _MockAdminUser()

    # Fall back to JWT validation (web admin panel)
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fast-path: fixed admin UUID used by the web admin panel login
    _FIXED_ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
    if str(user_id) == _FIXED_ADMIN_UUID:
        return _MockAdminUser()

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is banned",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
