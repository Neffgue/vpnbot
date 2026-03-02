from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from backend.database import Base


class Referral(Base):
    """Referral bonus tracking model."""

    __tablename__ = "referrals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    referrer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    referred_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, unique=True)
    bonus_days = Column(Integer, default=7, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)  # When bonus was paid
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_given")
    referred_user = relationship("User", foreign_keys=[referred_id], back_populates="referrals_received")

    def __repr__(self):
        return f"<Referral {self.id}>"
