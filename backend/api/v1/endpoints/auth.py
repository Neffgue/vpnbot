import logging
import os
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import UserCreate, UserResponse
from backend.services.user_service import UserService
from backend.utils.security import create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False)),
) -> None:
    """Dependency: require valid API key in Authorization header."""
    _api_key = os.getenv("API_KEY", "")
    token = credentials.credentials if credentials else None
    if not _api_key or token != _api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, dependencies=[Depends(_require_api_key)])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user with Telegram ID.
    Requires valid API key — internal bot endpoint only.
    """
    service = UserService(db)

    # Check if user exists
    existing = await service.get_user_by_telegram_id(user_data.telegram_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered",
        )

    # Validate referred_by if provided
    if user_data.referred_by:
        referrer = await service.get_user(user_data.referred_by)
        if not referrer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referrer not found",
            )

    user = await service.create_user(
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        first_name=user_data.first_name,
        referred_by=user_data.referred_by,
    )

    logger.info(f"User registered: {user.telegram_id}")
    return user


@router.post("/token", dependencies=[Depends(_require_api_key)])
async def get_token(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get JWT tokens for a user.
    Requires valid API key in Authorization header (bot-internal endpoint).
    """
    service = UserService(db)
    user = await service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is banned",
        )

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"Tokens issued for user: {user.telegram_id}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token (accepts JSON body).
    """
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    service = UserService(db)
    user = await service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is banned",
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info(f"Token refreshed for user: {user.id}")

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def admin_login(login_data: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Admin login with username/password from environment variables.
    """
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    if login_data.username != admin_username or login_data.password != admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Find or create admin user in DB
    service = UserService(db)
    
    # Use a special admin telegram_id (from env ADMIN_IDS)
    admin_ids_str = os.getenv("ADMIN_IDS", os.getenv("TELEGRAM_ADMIN_IDS", "0"))
    admin_telegram_id = int(admin_ids_str.split(",")[0].strip() or "0")
    
    # Always use the fixed admin UUID so we have a stable admin user in DB
    admin_user_id = "00000000-0000-0000-0000-000000000001"
    result = await db.execute(sa_select(User).where(User.id == admin_user_id))
    admin_user = result.scalars().first()
    if not admin_user:
        # Use telegram_id=-1 for the panel admin (reserved, won't conflict with real users)
        admin_user = User(
            id=admin_user_id,
            telegram_id=-1,
            username=admin_username,
            first_name="Admin",
            is_admin=True,
            referral_code="ADMIN",
        )
        db.add(admin_user)
        try:
            await db.commit()
            await db.refresh(admin_user)
        except Exception:
            await db.rollback()
            # If creation failed (e.g. telegram_id=-1 conflicts), just look it up again
            result = await db.execute(sa_select(User).where(User.id == admin_user_id))
            admin_user = result.scalars().first()
    
    if admin_user and not admin_user.is_admin:
        # Ensure admin flag is set (in case it was cleared)
        admin_user.is_admin = True
        await db.commit()
        await db.refresh(admin_user)
    
    # If still no admin_user, fall back to finding by telegram_id from env
    if not admin_user and admin_telegram_id:
        admin_user = await service.get_user_by_telegram_id(admin_telegram_id)
        if admin_user and not admin_user.is_admin:
            admin_user.is_admin = True
            await db.commit()
            await db.refresh(admin_user)
    
    access_token = create_access_token(data={"sub": admin_user.id})
    refresh_token = create_refresh_token(data={"sub": admin_user.id})
    
    logger.info(f"Admin login successful: {login_data.username}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": admin_user.id,
            "username": admin_username,
            "is_admin": True,
        }
    }


