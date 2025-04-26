from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_KEY: str = "your-default-api-key"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    ALLOWED_ORIGINS: List[str] = ["*"]
    agent_cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"

settings = Settings()