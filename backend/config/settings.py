from pydantic_settings import BaseSettings  # Use pydantic_settings
from typing import List, Optional

class SecuritySettings(BaseSettings):
    JWT_SECRET_KEY: str = "default-secret-key"  # Provide a default value
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if value == "default-secret-key":
            raise ValueError("JWT_SECRET_KEY is not set. Please configure it in the environment.")
        return value

class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"

class ApiKeySettings(BaseSettings):
    ALPHA_VANTAGE_KEY: str = "default-alpha-vantage-key"  # Provide a default value
    POLYGON_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    YAHOO_FINANCE_API_KEY: Optional[str] = None

    @classmethod
    def validate_alpha_vantage_key(cls, value: str) -> str:
        if value == "default-alpha-vantage-key":
            raise ValueError("ALPHA_VANTAGE_KEY is not set. Please configure it in the environment.")
        return value

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
    brain_smoothing_window: int = 10  # Default value for brain smoothing window
    REDIS_HOST: str = "localhost"  # Default Redis host

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'allow'  # Allow extra fields in environment variables

def get_settings() -> Settings:
    """Returns an instance of the Settings class."""
    return Settings()

settings = get_settings()