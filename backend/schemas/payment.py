from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    """Payment creation schema."""
    plan_name: str
    period_days: int


class PaymentResponse(BaseModel):
    """Payment response schema."""
    id: str
    user_id: str
    amount: Decimal
    currency: str
    provider: str
    provider_payment_id: str
    status: str
    plan_name: str
    period_days: int
    device_limit: int
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentWebhookYooKassa(BaseModel):
    """YooKassa webhook payload schema."""
    type: str
    event: str
    data: dict


class PaymentCallbackTelegramStars(BaseModel):
    """Telegram Stars callback payload schema."""
    update_id: int
    pre_checkout_query: Optional[dict] = None
    successful_payment_checkout: Optional[dict] = None
