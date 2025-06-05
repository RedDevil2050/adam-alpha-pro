import asyncio
import json  # Import json for deserialization
from typing import Dict, Any
import pandas as pd
from backend.utils.cache_utils import get_redis_client


class MarketContext:
    _instance = None

    def __init__(self, data_provider=None, settings=None):
        self.cache = None
        self.state = {}
        self.update_interval = 300  # 5 minutes
        self._lock = asyncio.Lock()
        self.data_provider = data_provider  # Store if provided
        self.settings = settings  # Store if provided
        # Potentially use self.settings to configure update_interval or other params
        if self.settings and hasattr(self.settings, 'market_context_update_interval'):
            self.update_interval = self.settings.market_context_update_interval

    @classmethod
    async def get_instance(cls, data_provider=None, settings=None):  # Add params
        if not cls._instance:
            # Pass data_provider and settings to constructor if provided
            cls._instance = cls(data_provider=data_provider, settings=settings)
            await cls._instance.initialize()
        # If instance exists, but new DP/settings are provided, re-initialize (optional, depends on desired behavior)        # For now, we assume that if get_instance is called with new params, it's for the initial creation
        # or a specific re-configuration scenario that the caller is managing.
        # If the instance exists and no new params, just return it.
        return cls._instance

    async def initialize(self):
        """Initialize market context"""
        if not self.cache:  # Initialize cache only if not already set (e.g. by a test mock)
            self.cache = await get_redis_client()

        # Load initial state from cache
        self.state = await self._load_state()

        # Start the auto-update task only if it's not already running
        # This check is a bit tricky as tasks don't have a simple "is_running" attribute.
        # A more robust way would be to store the task future and check its state.
        # For simplicity, we'll assume initialize is called once per instance effectively.
        # If _auto_update_task is None or done, create new.
        if not hasattr(self, '_auto_update_task') or self._auto_update_task.done():
            self._auto_update_task = asyncio.create_task(self._auto_update())

    async def get_state(self, symbol: str = None) -> Dict[str, Any]:
        """Get market state, optionally filtered by symbol"""
        async with self._lock:
            if symbol:
                # Return a copy to prevent external modification
                return self.state.get(symbol, {}).copy()
            # Return a copy of the entire state
            return self.state.copy()

    async def _load_state(self) -> Dict[str, Any]:
        """Load market state from cache (Redis)."""
        if not self.cache:
            print("Error: Cache not initialized before loading state.")
            return {}
        try:
            state_json = await self.cache.get("market_state")
            if state_json:
                # Deserialize the JSON string back into a Python dict
                loaded_state = json.loads(state_json)
                print("Market state loaded from cache.")
                return loaded_state
            else:
                print("No market state found in cache, starting fresh.")
                return {}
        except Exception as e:
            print(f"Error loading market state from cache: {e}")
            return {}  # Return empty dict on error

    async def _update_state(self):
        """Placeholder for the logic that updates the market state."""
        # In a real implementation, this would fetch new data,
        # run analyses (like market regime detection), and update self.state.
        # For now, it just simulates saving the current state.
        async with self._lock:
            # Example: Update a timestamp or a dummy value
            self.state['last_updated'] = pd.Timestamp.now().isoformat()
            # Persist the updated state back to Redis
            try:
                if self.cache:
                    # Serialize the state dictionary to a JSON string
                    state_json = json.dumps(self.state)
                    await self.cache.set("market_state", state_json)
                    # Optional: Set an expiration time if desired
                    # await self.cache.expire("market_state", 3600)  # e.g., 1 hour
                    print("Market state saved to cache.")
            except Exception as e:
                print(f"Error saving market state to cache: {e}")

    async def _auto_update(self):
        """Auto-update market state"""
        while True:
            try:
                await self._update_state()
            except Exception as e:
                print(f"Market state update error: {e}")
            # Use the defined interval
            await asyncio.sleep(self.update_interval)
