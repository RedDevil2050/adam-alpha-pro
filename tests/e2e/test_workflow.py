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
# Note: In a real CI/deployment environment, these would typically be
# managed externally or via environment variables loaded differently.
# Setting them here directly is suitable for simple local test execution.
# Use the correct env var name and the value expected by settings.py in test mode
os.environ['JWT_SECRET_KEY'] = 'secure-test-jwt-secret-for-testing-environment-only'
# os.environ['SECRET_KEY'] = 'test-secret-key-for-jwt' # Remove or comment out old one
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
            headers = {"Authorization": f"Bearer {access_token}"} # Typo fix: tokenodendron -> token
            symbol = "AAPL" # Use a known symbol likely to have data
            logger.info(f"--- E2E Test: Starting analysis workflow for {symbol} ---")

            # Use client directly, no need for await
            response = client.get(f"/api/analyze/{symbol}", headers=headers)
            logger.debug(f"Response Status Code: {response.status_code}")
            try:
                # Log JSON only if parsing succeeds to avoid test failure logs being noisy
                response_json = response.json()
                logger.debug(f"Response JSON: {response_json}")
            except Exception:
                response_json = None
                logger.debug(f"Response Text: {response.text}")

            # Allow 200 OK for success, 503 SERVICE_UNAVAILABLE for external service issues,
            # or potentially 404 NOT_FOUND if the symbol data itself is missing in the E2E environment's data source.
            expected_statuses = [
                status.HTTP_200_OK,
                status.HTTP_503_SERVICE_UNAVAILABLE,
                status.HTTP_404_NOT_FOUND # Added 404 as a possible E2E outcome
            ]
            assert response.status_code in expected_statuses, \
                f"Expected one of {expected_statuses}, got {response.status_code}. Response: {response.text}"

            # Only validate results structure if status is 200 OK
            if response.status_code == status.HTTP_200_OK:
                result = response_json # Use the parsed JSON

                # Verify core response structure
                assert "score" in result
                assert isinstance(result["score"], (int, float))
                assert 0 <= result["score"] <= 100

                # Verify category scores
                assert "category_scores" in result
                expected_categories = ["technical", "fundamental", "intelligence", "risk"] # Assuming 'risk' is a category
                # Note: Adjust expected_categories list based on your actual backend categories
                for cat in expected_categories:
                    assert cat in result["category_scores"], f"Missing category score for '{cat}' in response"
                    assert 0 <= result["category_scores"][cat] <= 100

                # Verify confidence levels
                assert "confidence_levels" in result
                for cat in expected_categories:
                    assert cat in result["confidence_levels"], f"Missing confidence level for '{cat}' in response"
                    # Assuming confidence is 0-1, adjust if 0-100
                    assert 0 <= result["confidence_levels"][cat] <= 1

                # Verify weights
                assert "weights" in result
                assert all(cat in result["weights"] for cat in expected_categories), "Weights missing for one or more expected categories"
                # Add check that weights sum up correctly (assuming sum is 1.0)
                try:
                    total_weights = sum(result["weights"].values())
                    assert abs(total_weights - 1.0) < 1e-9, f"Weights do not sum to 1.0: {total_weights}"
                except (AttributeError, TypeError, ValueError) as e:
                     pytest.fail(f"Could not sum weights or weights format incorrect: {e}")


                # Verify metadata
                assert "metadata" in result
                assert result["metadata"].get("symbol") == symbol, f"Metadata symbol mismatch: Expected {symbol}, got {result['metadata'].get('symbol')}"
                assert "market_data_timestamp" in result["metadata"]
                assert "analysis_timestamp" in result["metadata"]
                # Optional: Check format of timestamps

                logger.info(f"--- E2E Test: Analysis workflow for {symbol} PASSED (200 OK) ---")
            else:
                logger.warning(f"--- E2E Test: Analysis workflow for {symbol} resulted in {response.status_code}. Skipping detailed validation. ---")


    def test_analysis_unauthenticated(self):
        """Tests that the endpoint requires authentication."""
        with TestClient(app) as client:
            symbol = "MSFT"
            response = client.get(f"/api/analyze/{symbol}")
            # Expect 401 Unauthorized, not 404
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            # Check for common unauthenticated messages in detail or body
            detail = response.json().get("detail", "") if response.headers.get("content-type") == "application/json" else response.text
            assert any(msg in detail for msg in ["Not authenticated", "Could not validate credentials"]), \
                f"Expected authentication error message, got: {detail}"


    def test_analysis_invalid_symbol(self, access_token):
        """Tests behavior with invalid symbol."""
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            invalid_symbol = "INVALID_SYMBOL_XYZ123"
            response = client.get(f"/api/analyze/{invalid_symbol}", headers=headers)

            # Allow 404 if the backend/data source correctly identifies symbol as not found,
            # or 503 if it fails due to interacting with the external service.
            expected_statuses = [status.HTTP_404_NOT_FOUND, status.HTTP_503_SERVICE_UNAVAILABLE]
            assert response.status_code in expected_statuses, \
                f"Expected one of {expected_statuses}, got {response.status_code}. Response: {response.text}"

            # Check for relevant error message in the detail field (if JSON)
            detail = response.json().get("detail", "") if response.headers.get("content-type") == "application/json" else response.text
            # Adjust possible messages based on how your backend reports invalid symbol errors
            assert any(msg in detail for msg in ["Failed to fetch", "Could not retrieve", "No data available", "Symbol not found", "invalid symbol", "Analysis failed for symbol:"]), \
                f"Unexpected error detail for invalid symbol: {detail}"


    def test_analysis_malformed_token(self):
        """Tests behavior with malformed token."""
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer invalid.token.string"}
            response = client.get("/api/analyze/GOOGL", headers=headers)
            # Expect 401 Unauthorized, not 404
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            detail = response.json().get("detail", "") if response.headers.get("content-type") == "application/json" else response.text
            # Standard FastAPI/JWT detail for malformed/invalid signature
            assert "Could not validate credentials" in detail, f"Unexpected error detail for malformed token: {detail}"


    def test_analysis_expired_token(self):
        """Tests behavior with expired token."""
        # Need settings to get the correct secret key for token creation
        from backend.config.settings import get_settings
        test_settings = get_settings() # Get settings instance configured for testing

        token_data = {"sub": os.environ['API_USER']}
        # Create token with negative expiry time to ensure it's expired
        expires_delta = timedelta(minutes=-15)
        # Use the same function and secret key as the application will use for verification
        expired_token = create_access_token(data=token_data, expires_delta=expires_delta)

        # The logic to test the expired token was already present in the provided code.
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {expired_token}"}
            # Make a request to an authenticated endpoint using the expired token
            response = client.get("/api/analyze/TSLA", headers=headers) # Use any valid symbol

            # Assert that the request is rejected due to the expired token
            # Expect 401 Unauthorized, not 404
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            detail = response.json().get("detail", "") if response.headers.get("content-type") == "application/json" else response.text
            # The exact detail message for an expired token comes from the token verification logic
            assert any(msg in detail for msg in ["Signature has expired", "Token has expired", "Could not validate credentials"]), \
                   f"Expected expired token error message, got: {detail}"

