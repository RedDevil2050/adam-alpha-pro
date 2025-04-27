from pydantic_settings import BaseSettings
from typing import Optional, Dict
from functools import lru_cache
import json

class SecuritySettings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_KEY_HEADER: str = "X-API-Key"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

class DataProviderSettings(BaseSettings):
    ALPHA_VANTAGE_KEY: str
    YAHOO_FINANCE_API_KEY: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    
    # Scraping configs (with delays to respect Terms of Service)
    SCRAPING_ENABLED: bool = True
    SCRAPING_DELAY: float = 2.0
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

class CacheSettings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: Dict[str, int] = {
        "price": 300,        # 5 minutes
        "fundamentals": 3600, # 1 hour
        "analysis": 1800     # 30 minutes
    }

class MonitoringSettings(BaseSettings):
    ENABLE_PROMETHEUS: bool = True
    METRICS_PORT: int = 9090
    ALERT_WEBHOOK_URL: Optional[str] = None
    ERROR_NOTIFICATION_EMAIL: Optional[str] = None

class Settings(BaseSettings):
    security: SecuritySettings = SecuritySettings()
    data_provider: DataProviderSettings = DataProviderSettings()
    cache: CacheSettings = CacheSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    # Global settings
    ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name == "CACHE_TTL":
                return json.loads(raw_val)
            return raw_val

@lru_cache()
def get_settings() -> Settings:
    return Settings()