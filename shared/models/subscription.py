from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from .base import BaseModel


class Subscription(BaseModel):
    __tablename__ = "subscriptions"
    
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Subscription details
    plan_name = Column(String, nullable=False)  # 7d, 30d, 90d
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="USD")
    
    # Timing
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_trial = Column(Boolean, default=False)
    
    # Payment
    payment_provider = Column(String, nullable=True)  # telegram_stars, cryptocloud
    payment_id = Column(String, nullable=True)
    
    # Daily free usage tracking
    daily_messages_used = Column(BigInteger, default=0)
    daily_messages_limit = Column(BigInteger, default=5)
    daily_reset_at = Column(DateTime, nullable=True)  # When daily limit resets
    
    # Relationships
    user = relationship("User", back_populates="subscription")