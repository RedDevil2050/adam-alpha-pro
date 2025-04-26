import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.valuation.pe_ratio_agent import run as pe_run

@pytest.mark.asyncio
async def test_pe_ratio_agent_httpx(httpx_mock):
    # Mock price and eps endpoints
    httpx_mock.add_response(
        url="https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=TCS&apikey=demo",
        json={"Global Quote": {"05. price": "200.00"}}
    )
    httpx_mock.add_response(
        url="https://www.alphavantage.co/query?function=OVERVIEW&symbol=TCS&apikey=demo",
        json={"EPS": "10.00"}
    )
    res = await pe_run('TCS', {})
    assert res['pe_ratio'] == pytest.approx(20.0, rel=1e-2)
    assert res['verdict'] == 'buy'