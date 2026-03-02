import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://vpn_user:vpn_password@localhost:5432/vpn_db",
    )

    # JWT — поддерживаем оба имени переменной
    SECRET_KEY: str = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "VPN Sales System API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_API_URL: str = "https://api.telegram.org/bot"

    # YooKassa
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_API_KEY: str = os.getenv("YOOKASSA_API_KEY", "")
    YOOKASSA_API_URL: str = "https://api.yookassa.ru/v3"

    # 3x-ui
    XUI_API_TIMEOUT: int = 30

    # Crypto
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY", None)

    # API Key (used by Telegram bot to access admin endpoints)
    API_KEY: str = os.getenv("API_KEY", "")

    # CORS
    ALLOWED_ORIGINS: list = ["*"]

    class Config:
        env_file = (".env.local", ".env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
