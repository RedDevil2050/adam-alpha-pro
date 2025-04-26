import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.utils.data_provider import (
    fetch_price_trendlyne, fetch_price_tickertape,
    fetch_price_moneycontrol, fetch_price_stockedge,
    fetch_price_tradingview, fetch_price_nse, fetch_price_bse,
    fetch_news_mint, fetch_news_bs, fetch_news_et
)

@pytest.mark.asyncio
async def test_trendlyne(monkeypatch):
    class R: text = "<div class='company-header__LTP'>100.0</div>"
    monkeypatch.setattr("httpx.AsyncClient.get", lambda self, url: R())
    assert await fetch_price_trendlyne("INFY") == 100.0

