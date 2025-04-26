import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import time
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("API_PASS", "testpass")
    monkeypatch.setenv("API_PASS_HASH", "$2b$12$examplehash")
    monkeypatch.setenv("JWT_SECRET", "jwtsecret")
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "demo")
    return monkeypatch

def test_api_analyze_and_results_flow():
    # Login
    resp = client.post("/login", json={"username":"admin","password":"testpass"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Submit job
    resp2 = client.post("/analyze", json={"symbol":"TCS"}, headers=headers)
    assert resp2.status_code == 202
    job_id = resp2.json()["job_id"]
    # Poll for completion
    timeout = time.time() + 10
    result = None
    while time.time() < timeout:
        res3 = client.get(f"/results/{job_id}", headers=headers)
        data = res3.json()
        if data.get("status") == "COMPLETE":
            result = data
            break
        time.sleep(1)
    assert result is not None
    assert "brain" in result