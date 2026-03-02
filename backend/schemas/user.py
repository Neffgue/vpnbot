from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user schema."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    email: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    referral_code: str = Field(..., min_length=5, max_length=10)
    referred_by: Optional[str] = None


class UserUpdate(BaseModel):
    """User update schema."""
    username: Optional[str] = None
    first_name: Optional[str] = None
    email: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""
    id: str
    referral_code: str
    balance: Decimal
    is_banned: bool
    is_admin: bool
    free_trial_used: bool
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response with additional info."""
    updated_at: datetime


class UserListResponse(BaseModel):
    """User list item response."""
    id: str
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    balance: Decimal
    is_banned: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True
