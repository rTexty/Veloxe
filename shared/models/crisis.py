from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class CrisisEvent(BaseModel):
    __tablename__ = "crisis_events"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Crisis data
    trigger_words = Column(Text, nullable=True)  # Words that triggered crisis mode
    severity = Column(String, default="HIGH")    # HIGH, MEDIUM, LOW
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_method = Column(String, nullable=True)  # safety_phrase, timeout, admin
    
    # Safety response
    safety_contacts_shown = Column(Boolean, default=False)
    user_confirmed_safety = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="crisis_events")