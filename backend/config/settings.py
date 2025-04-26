from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Environment settings 
    environment: str = "development"  # Changed from ENV
    log_level: str = "DEBUG"  # Changed from LOG_LEVEL
    
    # API settings
    API_KEY: Optional[str] = None
    MARKET_DATA_PROVIDER: str = "alpha_vantage"
    RATE_LIMIT: int = 300
    
    # Agent settings
    AGENT_CACHE_TTL: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="ZION_",  # Added prefix
        extra="allow"  # Allow extra fields
    )

settings = Settings()