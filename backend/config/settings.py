from pydantic import BaseSettings
from typing import Dict, List

class Settings(BaseSettings):
    API_KEYS: Dict[str, str]
    DATABASE_URL: str
    REDIS_URL: str
    MARKET_SETTINGS: Dict[str, any] = {
        'trading_hours': {
            'start': '09:30',
            'end': '16:00',
            'timezone': 'America/New_York'
        },
        'risk_limits': {
            'max_position_size': 0.1,
            'max_drawdown': 0.15,
            'volatility_target': 0.12
        },
        'execution': {
            'max_slippage': 0.0015,
            'min_liquidity': 1000000
        }
    }

    class Config:
        env_file = ".env"