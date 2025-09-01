from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    bot_token: str
    openai_api_key: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    admin_secret: str
    cryptocloud_api_key: Optional[str] = None
    
    class Config:
        # Look for .env file in project root
        env_file = os.path.join(os.path.dirname(__file__), "../..", ".env")


settings = Settings()