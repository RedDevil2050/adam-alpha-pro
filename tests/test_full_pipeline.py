import pytest
import time
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.orchestrator import run_full_cycle
from prometheus_client import generate_latest
import os
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import pandas as pd

client = TestClient(app)

@pytest.fixture(scope="session")
def token():
    resp = client.post("/api/login", json={"username": os.getenv("API_USER", "admin"), "password": os.getenv("API_PASS", "changeme")})
    if resp.status_code != 200:
        pytest.skip("Login failed, skipping tests")
    return resp.json().get("access_token")

def test_health():
    # Use the correct health endpoint path defined in the backend API
    resp = client.get("/api/health") 
    # Check for 200 OK or 503 Service Unavailable (if unhealthy)
    # Allow unhealthy state as long as the endpoint itself works
    assert resp.status_code in [200, 503]
    # Check if the response is JSON and contains the 'status' key
    try:
        # Assert status is within the detail dictionary
        assert "status" in resp.json().get("detail", {})
    except Exception as e:
        pytest.fail(f"Health endpoint did not return valid JSON or expected structure: {e}\nResponse text: {resp.text}")

def test_metrics_endpoint(token):
    text = client.get("/api/v1/metrics").text
    # Check for the actual metrics that are being exposed
    assert "zion_agent_execution_time_seconds" in text
    assert "zion_agent_executions_total" in text
    assert "zion_cache_hits_total" in text
    assert "zion_cache_misses_total" in text
    assert "zion_system_cpu_usage_percent" in text
    assert "zion_system_memory_usage_percent" in text

@pytest.mark.asyncio
async def test_orchestrator_generic():
    # Mock the global provider instance to avoid external API calls
    with patch('backend.utils.data_provider.provider') as mock_provider:
        # Mock all the commonly used provider methods
        mock_provider.fetch_data_resilient = AsyncMock(return_value={
            "source": "mock",
            "data": {
                "price": 2500.0,
                "volume": 1000000,
                "market_cap": 500000000000,
                "pe_ratio": 18.5
            },
            "confidence": "high"
        })
        mock_provider.fetch_price_data = AsyncMock(return_value=pd.DataFrame({
            'open': [2400.0, 2450.0, 2500.0],
            'high': [2420.0, 2470.0, 2520.0],
            'low': [2380.0, 2430.0, 2480.0],
            'close': [2410.0, 2460.0, 2510.0],
            'volume': [1000000, 1100000, 1200000]
        }))
        mock_provider.fetch_quote = AsyncMock(return_value={"price": 2500.0, "volume": 1000000})
        mock_provider.fetch_company_info = AsyncMock(return_value={"market_cap": 500000000000, "pe_ratio": 18.5})
        
        # Also patch the UnifiedDataProvider class for direct instantiation
        with patch('backend.data.providers.unified_provider.UnifiedDataProvider') as mock_provider_class:
            mock_instance = mock_provider_class.return_value
            mock_instance.fetch_data_resilient = mock_provider.fetch_data_resilient
            mock_instance.fetch_price_data = mock_provider.fetch_price_data
            mock_instance.fetch_quote = mock_provider.fetch_quote
            mock_instance.fetch_company_info = mock_provider.fetch_company_info
            
            result = await run_full_cycle("RELIANCE")
            assert isinstance(result, dict)
            # must contain at least one agent
            assert any(k not in ["brain", "symbol", "status"] for k in result)

def test_analyze_and_results(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Mock the run_full_cycle function to avoid external API calls
    mock_analysis_result = {
        "status": "COMPLETE",
        "symbol": "RELIANCE",
        "brain": {
            "result": "Mock analysis completed successfully",
            "confidence": 0.85,
            "recommendations": ["BUY", "HOLD"],
            "risk_assessment": "MODERATE"
        },
        "agents": {
            "technical_analysis": {"status": "SUCCESS", "data": {"rsi": 65.5, "macd": "bullish"}},
            "fundamental_analysis": {"status": "SUCCESS", "data": {"pe_ratio": 18.5, "eps": 45.2}},
            "sentiment_analysis": {"status": "SUCCESS", "data": {"sentiment_score": 0.7, "news_count": 15}}
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
    
    # Use the correct API design with GET endpoint and mock the orchestrator
    with patch('backend.api.endpoints.analysis.run_full_cycle', new_callable=AsyncMock) as mock_run_analysis:
        mock_run_analysis.return_value = mock_analysis_result
        
        resp = client.get("/api/analyze/RELIANCE", headers=headers)
        
        assert resp.status_code == 200, f"Analysis request failed: {resp.text}"
        data = resp.json()
        assert data is not None, "Analysis did not complete"
        assert "brain" in data
        assert data["status"] == "COMPLETE"
        assert data["symbol"] == "RELIANCE"

def test_rate_limit_skip():
    # if AV free-tier limit reached, skip
    resp = client.get("/api/analyze/TCS")
    if "Thank you for using Alpha Vantage" in resp.text:
        pytest.skip("AV rate-limited")
