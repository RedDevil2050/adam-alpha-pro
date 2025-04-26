import os

def prepare_for_gemini(project_root: str):
    """
    Automates updates to:
    - Dockerfile.frontend: install retry and metrics libs
    - Requirements: ensure all dependencies
    - Tests: replace existing tests with generic, login-based tests
    """
    # 1. Update requirements
    req_path = os.path.join(project_root, 'requirements.txt')
    with open(req_path) as f:
        lines = f.read().splitlines()
    deps = ['prometheus-client', 'tenacity']
    with open(req_path, 'a') as f:
        for dep in deps:
            if dep not in lines:
                f.write(f"\n{dep}")

    # 2. Update Dockerfile.frontend
    df_front = os.path.join(project_root, 'Dockerfile.frontend')
    df_lines = []
    with open(df_front) as f:
        for line in f:
            df_lines.append(line.rstrip())
            if 'pip install streamlit' in line:
                df_lines.append('RUN pip install --no-cache-dir prometheus-client tenacity')
    with open(df_front, 'w') as f:
        f.write("\n".join(df_lines) + "\n")

    # 3. Create new unified test suite
    tests_dir = os.path.join(project_root, 'tests')
    os.makedirs(tests_dir, exist_ok=True)
    test_suite = '''
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.orchestrator import run_orchestration
from backend.brain import run as compute_brain
from backend.config.settings import settings

client = TestClient(app)

@pytest.fixture(scope="session")
def token():
    # Obtain JWT via login endpoint
    resp = client.post("/login", json={"username": settings.api_user, "password": settings.api_pass})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_login_failure():
    resp = client.post("/login", json={"username": "bad", "password": "bad"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_orchestrator_generic():
    result = await run_orchestration("RELIANCE")
    assert isinstance(result, dict)
    # Check first agent output has required keys
    _, output = next(iter(result.items()))
    assert "symbol" in output
    assert "verdict" in output

def test_analyze_and_results(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/analyze", json={"symbol": "RELIANCE"}, headers=headers)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    # Force run
    import asyncio
    from backend.api.main import _run_pipeline
    asyncio.run(_run_pipeline(job_id))
    res = client.get(f"/results/{job_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETE"
    assert "agent_outputs" in data
    assert "brain" in data

def test_metrics():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "agent_executions_total" in text
    assert "agent_errors_total" in text
'''

    with open(os.path.join(tests_dir, 'test_full_pipeline.py'), 'w') as f:
        f.write(test_suite.strip())

    print("Gemini prep complete: Requirements, Dockerfile.frontend, and tests updated.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        prepare_for_gemini(sys.argv[1])
    else:
        print("Usage: python gemini_prep.py <project_root>")
