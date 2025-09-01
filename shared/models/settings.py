from sqlalchemy import Column, String, Text, Integer, Boolean, JSON, DateTime
from .base import BaseModel


class Settings(BaseModel):
    __tablename__ = "bot_settings"
    
    # Setting identification
    key = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # frequent, expert
    
    # Values
    string_value = Column(Text, nullable=True)
    integer_value = Column(Integer, nullable=True)
    boolean_value = Column(Boolean, nullable=True)
    json_value = Column(JSON, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Audit
    changed_by = Column(String, nullable=True)  # admin user who made change
    changed_at = Column(DateTime, nullable=True)