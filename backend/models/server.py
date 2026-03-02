from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
from backend.database import Base
from backend.models.subscription import subscription_server_association


class Server(Base):
    """VPN Server model."""

    __tablename__ = "servers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)
    country_emoji = Column(String(10), nullable=False)
    country_name = Column(String(100), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    panel_url = Column(String(500), nullable=False)
    panel_username = Column(String(255), nullable=False)
    panel_password = Column(String(255), nullable=False)
    inbound_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    bypass_ru_whitelist = Column(Boolean, default=False, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subscriptions = relationship(
        "Subscription",
        secondary=subscription_server_association,
        back_populates="servers",
    )

    def __repr__(self):
        return f"<Server {self.name}>"
