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
    
    # Database settings
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    
    # Server settings
    host: Optional[str] = None
    port: Optional[str] = None
    workers: Optional[str] = None
    log_level: Optional[str] = None
    environment: Optional[str] = None
    debug: Optional[str] = None
    
    # Production settings
    sentry_dsn: Optional[str] = None
    use_ssl: Optional[str] = None
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    rate_limit_per_minute: Optional[str] = None
    max_concurrent_users: Optional[str] = None
    backup_enabled: Optional[str] = None
    backup_schedule: Optional[str] = None
    backup_retention_days: Optional[str] = None
    health_check_enabled: Optional[str] = None
    metrics_enabled: Optional[str] = None
    
    class Config:
        # Look for .env file in project root
        env_file = os.path.join(os.path.dirname(__file__), "../..", ".env")


settings = Settings()