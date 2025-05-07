import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app # Assuming main.py defines the FastAPI app
# Import necessary mocking tools
from unittest.mock import MagicMock, AsyncMock, patch

client = TestClient(app)

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    # Mock environment variables needed for the API
    monkeypatch.setenv("API_PASS", "testpass")
    # Use a known hash for testing if login relies on it
    # Example hash for "testpass" (generate a real one for actual use)
    monkeypatch.setenv("API_PASS_HASH", "$2b$12$EixZaYVK1fsAJC3Xl5j9.e6A6xKqkXQ3xHl3N8p.rQj/0pG0KzQk.")
    monkeypatch.setenv("JWT_SECRET", "jwtsecret")
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "demo")
    # Mock other necessary settings if required by the API endpoints
    # monkeypatch.setenv("REDIS_HOST", "localhost")
    # monkeypatch.setenv("REDIS_PORT", "6379")
    return monkeypatch

# Mock the background task execution
@pytest.fixture(autouse=True)
def mock_orchestrator(monkeypatch):
    # Mock run_full_cycle directly as the endpoint calls it synchronously
    mock_run_full_cycle = AsyncMock(return_value={"status": "COMPLETE", "brain": {"result": "mock_analysis"}})
    
    # Patch run_full_cycle where it's imported in the analysis endpoint module
    try:
        monkeypatch.setattr('backend.api.endpoints.analysis.run_full_cycle', mock_run_full_cycle)
    except AttributeError as e:
        pytest.fail(f"Failed to patch run_full_cycle. Check the import path in backend.api.endpoints.analysis. Error: {e}")
    
    # Return the mock if it needs to be accessed directly in a test (optional)
    return mock_run_full_cycle 


def test_api_analyze_and_results_flow():
    # Login - Assuming /api/login based on main.py prefix
    # The main.py doesn't show a /api/login endpoint. 
    # For now, I will assume the /api/analyze endpoint is protected and test it directly.
    # If login is indeed required and implemented elsewhere, this part needs adjustment.
    
    # For this test, let's assume verify_token is mocked or allows requests through in a test environment.
    # If verify_token is strict, it needs to be patched to simulate a valid token.
    with patch('backend.security.jwt_auth.verify_token', return_value={"sub": "testuser"}) as mock_verify_token:
        headers = {"Authorization": "Bearer faketesttoken"} # Token content doesn't matter due to mock

        # Call the analyze endpoint directly - it's a GET request in analysis.py
        # The test was trying to POST to /api/analyze, but the endpoint is GET /api/analyze/{symbol}
        symbol_to_test = "TCS"
        resp = client.get(f"/api/analyze/{symbol_to_test}", headers=headers)
        
        # Expect a direct result, not a job ID
        assert resp.status_code == 200, f"Analyze call failed: {resp.text}"
        result = resp.json()

        assert result is not None, "API did not return a result"
        assert result["status"] == "COMPLETE"
        assert "brain" in result
        assert result["brain"] == {"result": "mock_analysis"} # Check against mocked result