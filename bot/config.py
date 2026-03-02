"""Configuration module for VPN Sales Bot"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Загружаем .env из корня проекта (~/vpnbot/.env)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    token: str
    admin_ids: list[int]
    channel_url: str = "https://t.me/your_channel"
    support_url: str = "https://t.me/your_support"
    welcome_photo: str = ""  # File ID or URL for the welcome photo shown at /start


@dataclass
class APIConfig:
    """Backend API configuration"""
    base_url: str
    timeout: int = 30
    api_key: Optional[str] = None


@dataclass
class PaymentConfig:
    """Payment configuration"""
    yookassa_shop_id: str
    yookassa_api_key: str


@dataclass
class Config:
    """Main configuration class"""
    
    # Telegram settings — поддерживаем оба имени переменной
    telegram = TelegramConfig(
        token=os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN", ""),
        admin_ids=[
            int(x)
            for x in (
                os.getenv("TELEGRAM_ADMIN_IDS") or os.getenv("ADMIN_IDS", "")
            ).split(",")
            if x.strip()
        ],
        channel_url=os.getenv("TELEGRAM_CHANNEL_URL", "https://t.me/your_channel"),
        support_url=os.getenv("TELEGRAM_SUPPORT_URL", "https://t.me/your_support"),
        welcome_photo=os.getenv("WELCOME_PHOTO", ""),
    )
    
    # API settings
    api = APIConfig(
        base_url=os.getenv("API_BASE_URL", "http://localhost:8000/api"),
        timeout=int(os.getenv("API_TIMEOUT", "30")),
        api_key=os.getenv("API_KEY", ""),
    )
    
    # Payment settings
    payment = PaymentConfig(
        yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID", ""),
        yookassa_api_key=os.getenv("YOOKASSA_API_KEY", ""),
    )
    
    # Redis settings
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Database settings
    db_url: str = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Proxy для обхода блокировки Telegram (например: socks5://user:pass@host:port или http://host:port)
    proxy_url: str = os.getenv("PROXY_URL", "")

    # Debug mode
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Throttling settings (seconds)
    throttle_time: float = 10.0
    
    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration"""
        if not cls.telegram.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not cls.api.base_url:
            raise ValueError("API_BASE_URL is not set")
        return True


# Global config instance
config = Config()
