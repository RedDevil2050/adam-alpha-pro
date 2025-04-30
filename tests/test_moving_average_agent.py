import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.moving_average_agent import run as ma_run
from unittest.mock import AsyncMock # Import AsyncMock
import datetime # Import datetime

@pytest.mark.asyncio
async def test_moving_average_agent(monkeypatch):
    # Mock data matching expected OHLCV structure (need enough for window)
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(25, -1, -1)])
    prices_df = pd.DataFrame({
        'high': range(101, 128),
        'low': range(99, 126),
        'close': range(100, 127), # Simple increasing trend for testing slope
        'open': range(100, 127),
        'volume': [1000] * 27
    }, index=dates)

    # Mock fetch_ohlcv_series correctly
    mock_fetch = AsyncMock(return_value=prices_df)
    monkeypatch.setattr('backend.utils.data_provider.fetch_ohlcv_series', mock_fetch)

    # Mock redis client get/set methods
    mock_redis_get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_set = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.get = mock_redis_get
    mock_redis_client.set = mock_redis_set
    monkeypatch.setattr('backend.utils.cache_utils.get_redis_client', lambda: mock_redis_client)

    # Mock tracker (optional, but good practice)
    mock_tracker_update = AsyncMock()
    monkeypatch.setattr('backend.agents.technical.utils.tracker.update', mock_tracker_update)


    # Run the agent with a specific window