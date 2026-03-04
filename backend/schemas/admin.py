from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class UserBalanceUpdate(BaseModel):
    """Update user balance schema."""
    amount: Decimal
    reason: str = ""


class UserBanUpdate(BaseModel):
    """Ban/unban user schema."""
    user_id: str
    is_banned: bool


from typing import List

class BroadcastCreate(BaseModel):
    """Create broadcast schema."""
    message: str
    target: str = "all"  # all | active | trial | expired
    user_ids: Optional[List[int]] = None  # if None — send to all


class PlanPriceCreate(BaseModel):
    """Create plan price schema."""
    plan_name: str
    period_days: int
    price_rub: Decimal
    name: Optional[str] = None
    device_limit: Optional[int] = 1
    description: Optional[str] = None
    is_active: Optional[bool] = True


class PlanPriceUpdate(BaseModel):
    """Update plan price schema — все поля опциональны для частичного обновления."""
    plan_name: Optional[str] = None
    period_days: Optional[int] = None
    price_rub: Optional[Decimal] = None
    name: Optional[str] = None
    device_limit: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PlanPriceResponse(BaseModel):
    """Plan price response schema."""
    id: str
    plan_name: str
    period_days: int
    price_rub: Decimal
    name: Optional[str] = None
    device_limit: Optional[int] = 1
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BotTextCreate(BaseModel):
    """Create bot text schema."""
    key: str
    value: str
    description: Optional[str] = None


class BotTextUpdate(BaseModel):
    """Update bot text schema."""
    value: str
    description: Optional[str] = None


class BotTextResponse(BaseModel):
    """Bot text response schema."""
    id: str
    key: str
    value: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Admin statistics response."""
    total_users: int
    banned_users: int
    active_subscriptions: int
    total_revenue: Decimal
    pending_payments: int
    completed_payments: int
    # Dashboard extra fields
    revenue_today: Decimal = Decimal("0")
    revenue_month: Decimal = Decimal("0")
    active_servers: int = 0
    free_trials_used: int = 0
    active_referrals: int = 0
    monthly_revenue: Decimal = Decimal("0")


class SystemSettingsUpdate(BaseModel):
    """Update system-level settings (bot token, admin creds, etc.)."""
    bot_token: Optional[str] = None
    webhook_url: Optional[str] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    min_withdrawal: Optional[float] = None
    max_daily_withdrawal: Optional[float] = None
    referral_percent: Optional[float] = None


class SystemSettingsResponse(BaseModel):
    """System settings response (sensitive fields masked)."""
    bot_token: str = ""          # returned as-is so admin can see/verify it
    webhook_url: str = ""
    admin_username: str = "admin"
    min_withdrawal: float = 10.0
    max_daily_withdrawal: float = 1000.0
    referral_percent: float = 10.0
    # admin_password is never returned for security
