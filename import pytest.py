import pytest
from fastapi.testclient import TestClient
from ..backend.api.main import app
from ..backend.security.utils import create_access_token

client = TestClient(app)

def test_login_success():
    response = client.post(
        "/auth/token",
        data={"username": "test", "password": "test"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure():
    response = client.post(
        "/auth/token",
        data={"username": "wrong", "password": "wrong"}
    )
    assert response.status_code == 401

def test_protected_endpoint():
    token = create_access_token({"sub": "test"})
    response = client.get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
