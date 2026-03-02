from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ServerCreate(BaseModel):
    """Server creation schema."""
    name: str
    country_emoji: str
    country_name: str
    host: str
    port: int
    panel_url: str
    panel_username: str
    panel_password: str
    inbound_id: int
    bypass_ru_whitelist: bool = False
    order_index: int = 0


class ServerUpdate(BaseModel):
    """Server update schema."""
    name: Optional[str] = None
    country_emoji: Optional[str] = None
    country_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    panel_url: Optional[str] = None
    panel_username: Optional[str] = None
    panel_password: Optional[str] = None
    inbound_id: Optional[int] = None
    is_active: Optional[bool] = None
    bypass_ru_whitelist: Optional[bool] = None
    order_index: Optional[int] = None


class ServerResponse(BaseModel):
    """Server response schema."""
    id: str
    name: str
    country_emoji: str
    country_name: str
    host: str
    port: int
    is_active: bool
    bypass_ru_whitelist: bool
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True


class ServerDetailResponse(ServerResponse):
    """Detailed server response with panel credentials."""
    panel_url: str
    panel_username: str
    panel_password: str
    inbound_id: int
    updated_at: datetime
