# tests/e2e/test_workflow.py
import pytest
# Use FastAPI's TestClient instead of httpx.AsyncClient
# from httpx import AsyncClient
from fastapi.testclient import TestClient
from fastapi import status
from backend.api.main import app
from backend.security.jwt_auth import create_access_token
from datetime import timedelta
from loguru import logger
import os

# Set required environment variables for testing
os.environ['SECRET_KEY'] = 'test-secret-key-for-jwt'
os.environ['API_USER'] = 'test_e2e_user'
os.environ['API_PASS'] = 'test_password'

# No longer need asyncio marker if using synchronous TestClient
# @pytest.mark.asyncio
class TestCompleteWorkflow:

    @pytest.fixture(scope="class")
    def access_token(self):
        """Fixture to generate a valid access token for tests."""
        token_data = {"sub": os.environ['API_USER']}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data=token_data, expires_delta=expires_delta)
        logger.debug(f"Generated test token: {token[:10]}...")
        return token

    # Remove async keyword from test methods
    def test_analysis_workflow_success(self, access_token):
        """Tests the happy path for the analysis workflow."""
        # Use TestClient synchronously
        # async with AsyncClient(app=app, base_url="http://test") as client:
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            symbol = "AAPL"
            logger.info(f"--- E2E Test: Starting analysis workflow for {symbol} ---")

            # Use client directly, no need for await
            response = client.get(f"/api/analyze/{symbol}", headers=headers)
            logger.debug(f"Response Status Code: {response.status_code}")
            try:
                logger.debug(f"Response JSON: {response.json()}")
            except Exception:
                logger.debug(f"Response Text: {response.text}")

            assert response.status_code == status.HTTP_200_OK, \
                f"Expected 200 OK, got {response.status_code}. Response: {response.text}"

            result = response.json()

            # Verify core response structure
            assert "score" in result
            assert isinstance(result["score"], (int, float))
            assert 0 <= result["score"] <= 100

            # Verify category scores
            assert "category_scores" in result
            expected_categories = ["technical", "fundamental", "intelligence"]
            for cat in expected_categories:
                assert cat in result["category_scores"]
                assert 0 <= result["category_scores"][cat] <= 100

            # Verify confidence levels
            assert "confidence_levels" in result
            for cat in expected_categories:
                assert cat in result["confidence_levels"]
                assert 0 <= result["confidence_levels"][cat] <= 1

            # Verify weights
            assert "weights" in result
            assert all(cat in result["weights"] for cat in expected_categories)

            # Verify metadata
            assert "metadata" in result
            assert result["metadata"].get("symbol") == symbol
            assert "market_data_timestamp" in result["metadata"]
            assert "analysis_timestamp" in result["metadata"]

            logger.info(f"--- E2E Test: Analysis workflow for {symbol} PASSED ---")

    def test_analysis_unauthenticated(self):
        """Tests that the endpoint requires authentication."""
        with TestClient(app) as client:
            symbol = "MSFT"
            response = client.get(f"/api/analyze/{symbol}")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Not authenticated" in response.text or "Could not validate credentials" in response.text

    def test_analysis_invalid_symbol(self, access_token):
        """Tests behavior with invalid symbol."""
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            invalid_symbol = "INVALID_SYMBOL_XYZ123"
            response = client.get(f"/api/analyze/{invalid_symbol}", headers=headers)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            detail = response.json().get("detail", "")
            assert "Could not retrieve" in detail or "Failed to fetch market data" in detail

    def test_analysis_malformed_token(self):
        """Tests behavior with malformed token."""
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer invalid.token.string"}
            response = client.get("/api/analyze/GOOGL", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in response.json().get("detail", "")

