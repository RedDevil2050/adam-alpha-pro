import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.api.main import app # Assuming main.py defines the FastAPI app
# Import necessary mocking tools
from unittest.mock import MagicMock, AsyncMock, patch
# Import verify_token for dependency override
from backend.security.jwt_auth import verify_token

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
    # Override the verify_token dependency for this test
    async def mock_verify_token_override():
        return {"sub": "testuser"}
    
    app.dependency_overrides[verify_token] = mock_verify_token_override

    headers = {"Authorization": "Bearer faketesttoken"} # Token content doesn't matter due to override

    # Call the analyze endpoint directly - it's a GET request in analysis.py
    symbol_to_test = "TCS"
    # Ensure the mock for run_full_analysis_for_symbol is in place for the endpoint to use
    with patch('backend.api.endpoints.analysis.run_full_analysis_for_symbol', new_callable=AsyncMock) as mock_run_analysis:
        # Configure the mock to return a structure that the endpoint expects
        # The endpoint expects a dictionary that will be returned as JSON.
        # Based on the previous successful test, it should look something like:
        mock_run_analysis.return_value = {
            "status": "COMPLETE", 
            "brain": {"result": "mock_analysis"}, 
            "symbol": symbol_to_test, 
            "version": "1.0.0", # Add other fields if the endpoint returns them
            "timestamp": datetime.now().isoformat()
        }

        resp = client.get(f"/api/analyze/{symbol_to_test}", headers=headers)
    
    # Expect a direct result, not a job ID
    assert resp.status_code == 200, f"Analyze call failed: {resp.text}"
    result = resp.json()

    assert result is not None, "API did not return a result"
    assert result["status"] == "COMPLETE"
    assert "brain" in result
    assert result["brain"] == {"result": "mock_analysis"} # Check against mocked result

    # Clean up the dependency override after the test
    app.dependency_overrides = {}