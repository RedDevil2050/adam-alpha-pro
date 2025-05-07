import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from backend.agents.valuation.book_to_market_agent import run as bm_run
from unittest.mock import AsyncMock, patch, MagicMock # Import MagicMock

@pytest.mark.asyncio
# Patch yfinance.Ticker to prevent actual network calls
@patch('yfinance.Ticker', new_callable=MagicMock) 
@patch('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', new_callable=AsyncMock)
@patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', new_callable=AsyncMock)
async def test_book_to_market_agent(
    mock_fetch_book_value,
    mock_fetch_price_point,
    mock_fetch_hist_prices,
    mock_yfinance_ticker, # Add the yfinance.Ticker mock
    # monkeypatch
):
    # Mock dependencies
    mock_fetch_book_value.return_value = 50.0
    # This mock should now be fully effective as yfinance.Ticker is also mocked
    mock_fetch_price_point.return_value = 100.0 
    
    dates = pd.date_range(end='2025-05-03', periods=100)
    hist_prices_series = pd.Series(np.random.normal(100, 10, 100), index=dates)
    mock_fetch_hist_prices.return_value = hist_prices_series

    # Configure the yfinance.Ticker mock if its methods are called directly or indirectly
    # For instance, if ticker_instance.info or ticker_instance.history is called by the underlying
    # fetch_price_point (even if fetch_price_point itself is mocked at a higher level,
    # the yfinance.Ticker mock ensures no network activity if something slips through)
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.info = {} # Example: if .info is accessed
    # If .history() is called by the actual (unmocked) data_provider.py's fetch_price_point
    # despite our agent-level mock, this would catch it.
    # However, the agent-level mock of fetch_price_point should prevent this.
    # This yfinance.Ticker patch is more of a safety net.
    mock_yfinance_ticker.return_value = mock_ticker_instance


    res = await bm_run('ABC', {})

    # Assertions
    assert res['symbol'] == 'ABC'
    assert 'value' in res
    assert isinstance(res['value'], float)
    assert res['value'] == pytest.approx(0.5)
    assert 'details' in res
    assert 'btm_ratio' in res['details']
    assert res['details']['btm_ratio'] == res['value']
    assert 'verdict' in res
    assert res.get('error') is None