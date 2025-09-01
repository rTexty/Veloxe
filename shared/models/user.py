from sqlalchemy import Column, String, Boolean, BigInteger, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    age = Column(BigInteger, nullable=True)
    gender = Column(String, nullable=True)  # male, female, not_applicable
    city = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    
    # Consent and privacy
    terms_accepted = Column(Boolean, default=False)
    privacy_accepted = Column(Boolean, default=False)
    policy_version = Column(String, default="v1")
    accepted_at = Column(DateTime, nullable=True)
    
    # Profile data
    emotion_tags = Column(JSON, nullable=True)  # List of selected emotions
    topic_tags = Column(JSON, nullable=True)   # List of selected topics
    
    # Preferences
    ping_enabled = Column(Boolean, default=True)
    ping_hours_start = Column(BigInteger, default=10)  # 10:00
    ping_hours_end = Column(BigInteger, default=21)    # 21:00
    
    # Subscription reminder timestamps
    last_reminder_24h = Column(DateTime, nullable=True)
    last_reminder_expiry = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_in_crisis = Column(Boolean, default=False)
    crisis_freeze_until = Column(DateTime, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user")
    events = relationship("Event", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    crisis_events = relationship("CrisisEvent", back_populates="user")
    memory_anchors = relationship("MemoryAnchor", back_populates="user")