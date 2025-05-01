import asyncio
from typing import Dict, Any
import pandas as pd
from backend.utils.cache_utils import get_redis_client


class MarketContext:
    _instance = None

    def __init__(self):
        self.cache = None
        self.state = {}
        self.update_interval = 300  # 5 minutes
        self._lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        """Initialize market context"""
        self.cache = await get_redis_client()
        self.state = await self._load_state()
        asyncio.create_task(self._auto_update())

    async def get_state(self, symbol: str = None) -> Dict[str, Any]:
        """Get market state, optionally filtered by symbol"""
        async with self._lock:
            if symbol:
                return self.state.get(symbol, {})
            return self.state

    async def _auto_update(self):
        """Auto-update market state"""
        while True:
            try:
                await self._update_state()
            except Exception as e:
                print(f"Market state update error: {e}")
            await asyncio.sleep(self.update_interval)
