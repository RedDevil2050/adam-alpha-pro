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
    from backend.orchestrator import Orchestrator # Import inside fixture

    mock_instance = MagicMock(spec=Orchestrator)
    mock_instance.run_analysis_async = AsyncMock(return_value="test_job_id_123")
    # Mock get_status to simulate completion after a delay
    status_store = {"test_job_id_123": {"status": "PENDING"}}
    async def mock_get_status(job_id):
        if job_id == "test_job_id_123":
            if status_store[job_id]["status"] == "PENDING":
                 # Simulate completion after first check
                status_store[job_id] = {"status": "COMPLETE", "brain": {"result": "mock_analysis"}}
            return status_store[job_id]
        return {"status": "NOT_FOUND"}
    mock_instance.get_status = mock_get_status

    # Patch the Orchestrator instance where it's used in the analysis endpoint
    # Adjust the path 'backend.api.endpoints.analysis.orchestrator' if it's incorrect
    try:
        # Assuming the orchestrator instance is accessed via an import in the analysis endpoint module
        monkeypatch.setattr('backend.api.endpoints.analysis.orchestrator', mock_instance)
    except AttributeError:
         # Fallback if the path is different, adjust as necessary
         # Example: maybe it's imported directly in main?
         # monkeypatch.setattr('backend.api.main.orchestrator', mock_instance)
         pytest.fail("Failed to patch orchestrator. Check the path in backend.api.endpoints.analysis.")


def test_api_analyze_and_results_flow():
    # Login - Assuming /api/login based on main.py prefix
    resp = client.post("/api/login", json={"username":"admin","password":"testpass"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit job - Assuming /api/analyze
    resp2 = client.post("/api/analyze", json={"symbol":"TCS"}, headers=headers)
    assert resp2.status_code == 202, f"Analyze submission failed: {resp2.text}"
    job_id = resp2.json()["job_id"]
    assert job_id == "test_job_id_123" # Check against mocked return value

    # Poll for completion - Assuming /api/results/{job_id}
    timeout = time.time() + 10 # Increased timeout slightly
    result = None
    while time.time() < timeout:
        res3 = client.get(f"/api/results/{job_id}", headers=headers)
        assert res3.status_code == 200, f"Fetching results failed: {res3.text}"
        data = res3.json()
        if data.get("status") == "COMPLETE":
            result = data
            break
        time.sleep(0.5) # Shorter sleep for faster testing

    assert result is not None, "Polling timed out, result never completed"
    assert result["status"] == "COMPLETE"
    assert "brain" in result
    assert result["brain"] == {"result": "mock_analysis"} # Check against mocked result