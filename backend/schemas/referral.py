from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReferralResponse(BaseModel):
    """Referral response schema."""
    id: str
    referrer_id: str
    referred_id: str
    bonus_days: int
    paid_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ReferralStatsResponse(BaseModel):
    """Referral statistics response."""
    total_referrals: int
    paid_referrals: int
    pending_referrals: int
    total_bonus_days: int
