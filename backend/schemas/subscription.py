from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ServerSimple(BaseModel):
    """Simple server info for subscription response."""
    id: str
    name: str
    country_emoji: str
    country_name: str

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Subscription creation schema."""
    plan_name: str
    period_days: int


class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    is_active: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""
    id: str
    user_id: str
    plan_name: str
    device_limit: int
    traffic_gb: int
    expires_at: datetime
    is_active: bool
    xui_client_uuid: str
    created_at: datetime
    servers: List[ServerSimple] = []

    class Config:
        from_attributes = True


class SubscriptionDetailResponse(SubscriptionResponse):
    """Detailed subscription response."""
    updated_at: datetime
