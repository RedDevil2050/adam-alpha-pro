from pydantic_settings import BaseSettings  # Use pydantic_settings
from typing import List, Optional

class SecuritySettings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"

class ApiKeySettings(BaseSettings):
    ALPHA_VANTAGE_KEY: str
    POLYGON_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    YAHOO_FINANCE_API_KEY: Optional[str] = None

class MonitoringSettings(BaseSettings):
    SLACK_WEBHOOK_URL: Optional[str] = None
    EMAIL_NOTIFICATIONS: Optional[str] = None
    METRICS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"

class Settings(BaseSettings):
    security: SecuritySettings = SecuritySettings()
    redis: RedisSettings = RedisSettings()
    api_keys: ApiKeySettings = ApiKeySettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'