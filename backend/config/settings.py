
from pydantic_settings import BaseSettings
import os
import os
import os

from pydantic import root_validator

class Settings(BaseSettings):
    agent_cache_ttl: int = 3600
    vol_threshold: float = 0.05  # volatility threshold for regime shift
    brain_smoothing_window: int = 3  # smoothing window for final score
    alpha_vantage_key: str | None = None  # from ENV

settings = Settings()

settings = Settings()