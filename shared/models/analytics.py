from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class Event(BaseModel):
    __tablename__ = "analytics_events"
    
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)  # Note: This references the internal user ID, not Telegram ID
    
    # Event data
    event_type = Column(String, nullable=False, index=True)  # start, consent_accepted, etc.
    event_id = Column(String, nullable=True, index=True)     # For tracking flows
    
    # Data
    properties = Column(JSON, nullable=True)  # Additional event data
    
    # Privacy-safe metrics only (no personal content)
    message_length = Column(BigInteger, nullable=True)
    token_count = Column(BigInteger, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="events")


class UserSession(BaseModel):
    __tablename__ = "user_sessions"
    
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)  # Note: This references the internal user ID, not Telegram ID
    session_id = Column(String, nullable=False, index=True)
    
    # Session metrics
    message_count = Column(BigInteger, default=0)
    duration_minutes = Column(BigInteger, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime, nullable=True)
    end_reason = Column(String, nullable=True)  # timeout, user_exit, paywall, etc.
    
    # Relationships
    user = relationship("User", back_populates="sessions")