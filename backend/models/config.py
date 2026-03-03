from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from backend.database import Base


class PlanPrice(Base):
    """Plan pricing configuration."""

    __tablename__ = "plan_prices"
    __table_args__ = (
        UniqueConstraint("plan_name", "period_days", name="uq_plan_period"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    plan_name = Column(String(50), nullable=False)       # solo, family — технический ключ
    name = Column(String(100), nullable=True)            # Отображаемое имя: "👤 Соло", "👨‍👩‍👧 Семейный"
    period_days = Column(Integer, nullable=False)        # 7, 30, 90, 180, 365
    price_rub = Column(Numeric(12, 2), nullable=False)
    device_limit = Column(Integer, nullable=True, default=1)  # Количество устройств
    image_url = Column(String(500), nullable=True)       # URL картинки тарифа (из upload-image)
    description = Column(Text, nullable=True)            # Описание тарифа
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PlanPrice {self.plan_name} {self.period_days}d>"


class BotText(Base):
    """Configurable bot text/messages stored in database."""

    __tablename__ = "bot_texts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(String(4000), nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BotText {self.key}>"


class Broadcast(Base):
    """Broadcast messages for bot to send."""

    __tablename__ = "broadcasts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message = Column(String(4000), nullable=False)
    is_sent = Column(Integer, default=0, nullable=False)  # Number of users sent to
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Broadcast {self.id}>"
