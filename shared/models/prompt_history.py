from sqlalchemy import Column, String, Text, Integer, DateTime, func
from .base import BaseModel


class PromptHistory(BaseModel):
    __tablename__ = "prompt_history"
    
    # Prompt data
    prompt_text = Column(Text, nullable=False)
    prompt_type = Column(String(50), nullable=False, default="system_prompt", index=True)
    
    # Metadata
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    
    # Audit
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(DateTime, server_default=func.now())
    
    # State
    is_active = Column(String(10), nullable=False, default="inactive", index=True)  # active, inactive, archived