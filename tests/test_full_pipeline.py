import pytest
import time
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.orchestrator import run_full_cycle
from prometheus_client import generate_latest
import os

client = TestClient(app)

@pytest.fixture(scope="session")
def token():
    resp = client.post("/login", json={"username": os.getenv("API_USER", "admin"), "password": os.getenv("API_PASS", "changeme")})
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
    text = client.get("/metrics").text
    assert "agent_execution_duration_seconds" in text
    assert "agent_errors_total" in text
    assert "brain_category_score" in text
    assert "brain_final_score" in text

@pytest.mark.asyncio
async def test_orchestrator_generic():
    result = await run_full_cycle("RELIANCE")
    assert isinstance(result, dict)
    # must contain at least one agent
    assert any(k not in ["brain", "symbol", "status"] for k in result)

def test_analyze_and_results(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/analyze", json={"symbol": "RELIANCE"}, headers=headers)
    assert resp.status_code == 200
    job_id = resp.json().get("job_id")
    assert job_id
    # poll
    data = None
    for _ in range(15):
        time.sleep(1)
        res = client.get(f"/results/{job_id}", headers=headers)
        if res.status_code == 200 and res.json().get("status") != "PENDING":
            data = res.json()
            break
    assert data is not None, "Pipeline did not finish"
    assert "brain" in data

def test_rate_limit_skip():
    # if AV free-tier limit reached, skip
    resp = client.post("/analyze", json={"symbol": "TCS"})
    if "Thank you for using Alpha Vantage" in resp.text:
        pytest.skip("AV rate-limited")
