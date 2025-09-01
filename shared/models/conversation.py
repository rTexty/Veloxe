from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class Conversation(BaseModel):
    __tablename__ = "conversations"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=False, index=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    
    # Context
    memory_context = Column(Text, nullable=True)  # Long-term memory notes
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(BaseModel):
    __tablename__ = "messages"
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # Message data
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    
    # Metadata
    is_crisis_related = Column(Boolean, default=False)
    generated_blocks = Column(Integer, default=1)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")