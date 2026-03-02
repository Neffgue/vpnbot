from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import Column, DateTime, Numeric, String, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
from backend.database import Base


class Payment(Base):
    """Payment transaction model."""

    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    provider = Column(String(50), nullable=False)  # telegram_stars, yookassa
    provider_payment_id = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, completed, failed, refunded
    plan_name = Column(String(50), nullable=False)
    period_days = Column(Integer, nullable=False)
    device_limit = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id}>"
