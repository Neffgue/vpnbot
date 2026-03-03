from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Numeric, String, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    """User model for VPN system."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("telegram_id", name="uq_telegram_id"),
        UniqueConstraint("referral_code", name="uq_referral_code"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    telegram_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    referral_code = Column(String(10), nullable=False, unique=True, index=True)
    referred_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    balance = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    free_trial_used = Column(Boolean, default=False, nullable=False)
    auto_renewal = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    referrals_given = relationship(
        "Referral",
        foreign_keys="Referral.referrer_id",
        back_populates="referrer",
        cascade="all, delete-orphan",
    )
    referrals_received = relationship(
        "Referral",
        foreign_keys="Referral.referred_id",
        back_populates="referred_user",
        cascade="all, delete-orphan",
    )
    referrer = relationship("User", remote_side=[id], foreign_keys=[referred_by])

    def __repr__(self):
        return f"<User {self.telegram_id}>"
