from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from backend.database import Base



# Association table for many-to-many relationship
subscription_server_association = Table(
    "subscription_server_association",
    Base.metadata,
    Column("subscription_id", String(36), ForeignKey("subscriptions.id"), primary_key=True),
    Column("server_id", String(36), ForeignKey("servers.id"), primary_key=True),
)


class Subscription(Base):
    """Subscription model for user VPN access."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("xui_client_uuid", name="uq_xui_client_uuid"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    plan_name = Column(String(50), nullable=False)  # Solo, Family, Trial
    period_days = Column(Integer, nullable=False, default=30)
    device_limit = Column(Integer, nullable=False)
    traffic_gb = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    xui_client_uuid = Column(String(36), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Notification flags for expiry reminders
    notified_24h = Column(Boolean, default=False, nullable=False)
    notified_12h = Column(Boolean, default=False, nullable=False)
    notified_1h = Column(Boolean, default=False, nullable=False)
    notified_0h = Column(Boolean, default=False, nullable=False)
    notified_3h_after_expiry = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    servers = relationship(
        "Server",
        secondary=subscription_server_association,
        back_populates="subscriptions",
    )

    def __repr__(self):
        return f"<Subscription {self.id}>"
