import pytest
from httpx import AsyncClient
from fastapi import status  # Use status codes from FastAPI
from backend.api.main import app  # Import the app instance
from backend.security.utils import create_access_token  # Import token creation utility
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
class TestCompleteWorkflow:

    @pytest.fixture(scope="class")
    def access_token(self):
        """Fixture to generate a valid access token for tests."""
        token_data = {"sub": "test_e2e_user"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data=token_data, expires_delta=expires_delta)
        logger.debug(f"Generated test token: {token[:10]}...")
        return token

    async def test_analysis_workflow_success(self, access_token):
        """Tests the happy path for the analysis workflow."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # ...existing code...

    async def test_analysis_unauthenticated(self):
        """Tests that the endpoint requires authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # ...existing code...

    async def test_analysis_invalid_symbol(self, access_token):
        """Tests the behavior when an invalid symbol is provided."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # ...existing code...

    async def test_analysis_malformed_token(self):
        """Tests behavior with a malformed token."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # ...existing code...# tests/e2e/test_workflow.py
            import pytest
            from httpx import AsyncClient
            from fastapi import status # Use status codes from FastAPI
            
            # Import the app instance from your main application file
            # Adjust the import path based on your project structure
            from backend.api.main import app
            # Import the function to create tokens from your security utils
            from backend.security.utils import create_access_token
            from datetime import timedelta
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Use parametrize for different symbols if needed
            @pytest.mark.asyncio # Mark test class for asyncio
            class TestCompleteWorkflow:
            
                @pytest.fixture(scope="class")
                def access_token(self):
                    """Fixture to generate a valid access token for tests."""
                    # Use a test user subject. Ensure this user exists or is handled by your /auth/token logic
                    # if your tests hit the actual login endpoint first.
                    # For direct endpoint testing like this, generating a token is sufficient.
                    # Ensure the secret key used here matches the one used by the app.
                    token_data = {"sub": "test_e2e_user"}
                    # Set a reasonable expiry for the test token
                    expires_delta = timedelta(minutes=15)
                    token = create_access_token(data=token_data, expires_delta=expires_delta)
                    logger.debug(f"Generated test token: {token[:10]}...") # Log prefix for verification
                    return token
            
                async def test_analysis_workflow_success(self, access_token):
                    """
                    Tests the happy path for the analysis workflow:
                    Auth -> GET /api/analyze/{symbol} -> Orchestrator -> Brain -> 200 OK response.
                    """
                    # Use AsyncClient with the app instance for testing (doesn't require a running server)
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        headers = {"Authorization": f"Bearer {access_token}"}
                        symbol = "AAPL" # Use a common symbol likely to have data in mocks/providers
            
                        logger.info(f"--- E2E Test: Starting analysis workflow for {symbol} ---")
            
                        # 1. Make request to the correct analysis endpoint (GET)
                        response = await client.get(
                            f"/api/analyze/{symbol}",
                            headers=headers
                        )
            
                        # Log response details for debugging
                        logger.debug(f"Response Status Code: {response.status_code}")
                        try:
                             logger.debug(f"Response JSON: {response.json()}")
                        except Exception:
                             logger.debug(f"Response Text: {response.text}")
            
            
                        # 2. Assert Status Code
                        assert response.status_code == status.HTTP_200_OK, \
                            f"Expected 200 OK, got {response.status_code}. Response: {response.text}"
            
                        # 3. Parse and Verify Response Structure (based on Brain + Orchestrator output)
                        result = response.json()
            
                        # --- Assert Core Brain Output ---
                        assert "score" in result, "Response missing 'score'"
                        assert isinstance(result["score"], (int, float)), "'score' should be number"
                        assert 0 <= result["score"] <= 100, f"Score {result['score']} out of range [0, 100]"
            
                        assert "category_scores" in result, "Response missing 'category_scores'"
                        assert isinstance(result["category_scores"], dict), "'category_scores' should be a dict"
                        # Check specific categories if they are always expected from simulation/brain
                        # These depend on the simulated agents in orchestrator and brain weights
                        expected_categories = ["technical", "fundamental", "intelligence"]
                        for cat in expected_categories:
                             assert cat in result["category_scores"], f"Missing category '{cat}' in scores"
                             assert isinstance(result["category_scores"][cat], (int, float)), f"Score for '{cat}' not a number"
                             assert 0 <= result["category_scores"][cat] <= 100, f"Score for '{cat}' out of range"
            
                        assert "confidence_levels" in result, "Response missing 'confidence_levels'"
                        assert isinstance(result["confidence_levels"], dict), "'confidence_levels' should be a dict"
                        for cat in expected_categories:
                             assert cat in result["confidence_levels"], f"Missing category '{cat}' in confidence"
                             assert isinstance(result["confidence_levels"][cat], (int, float)), f"Confidence for '{cat}' not a number"
                             assert 0 <= result["confidence_levels"][cat] <= 1, f"Confidence for '{cat}' out of range [0, 1]"
            
                        assert "weights" in result, "Response missing 'weights'" # Brain adds weights used
                        assert isinstance(result["weights"], dict), "'weights' should be a dict"
                        # Check if weights match expected categories
                        assert all(cat in result["weights"] for cat in expected_categories), "Weights missing for expected categories"
            
                        # --- Assert Orchestrator Added Metadata ---
                        assert "metadata" in result, "Response missing 'metadata'"
                        assert isinstance(result["metadata"], dict), "'metadata' should be a dict"
                        assert result["metadata"].get("symbol") == symbol, f"Metadata symbol mismatch: expected {symbol}, got {result['metadata'].get('symbol')}"
                        assert "market_data_timestamp" in result["metadata"], "Metadata missing 'market_data_timestamp'"
                        assert "analysis_timestamp" in result["metadata"], "Metadata missing 'analysis_timestamp'" # Check for the timestamp added
            
                        logger.info(f"--- E2E Test: Analysis workflow for {symbol} PASSED ---")
            
            
                async def test_analysis_unauthenticated(self):
                    """Tests that the endpoint requires authentication."""
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        symbol = "MSFT"
                        logger.info(f"--- E2E Test: Starting unauthenticated request for {symbol} ---")
                        response = await client.get(f"/api/analyze/{symbol}") # No Authorization header
            
                        logger.debug(f"Response Status Code: {response.status_code}")
                        logger.debug(f"Response Text: {response.text}")
            
                        assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                            f"Expected 401 Unauthorized, got {response.status_code}"
                        assert "Not authenticated" in response.text or "Could not validate credentials" in response.text
            
                        logger.info(f"--- E2E Test: Unauthenticated request PASSED ---")
            
            
                async def test_analysis_invalid_symbol(self, access_token):
                    """
                    Tests the behavior when an invalid symbol is provided.
                    Expects a 404 Not Found if data_provider fails cleanly.
                    """
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        headers = {"Authorization": f"Bearer {access_token}"}
                        invalid_symbol = "INVALID_SYMBOL_XYZ123"
                        logger.info(f"--- E2E Test: Starting analysis for invalid symbol {invalid_symbol} ---")
            
                        response = await client.get(
                            f"/api/analyze/{invalid_symbol}",
                            headers=headers
                        )
            
                        logger.debug(f"Response Status Code: {response.status_code}")
                        logger.debug(f"Response Text: {response.text}")
            
                        # Expecting 404 if fetch_market_data raises ValueError which is handled in the endpoint
                        assert response.status_code == status.HTTP_404_NOT_FOUND, \
                             f"Expected 404 Not Found for invalid symbol, got {response.status_code}"
                        # Check if the detail message indicates data fetching failure
                        assert "Could not retrieve" in response.json().get("detail", "") or \
                               "Failed to fetch market data" in response.json().get("detail", ""), \
                               "Response detail did not indicate data fetching failure"
            
                        logger.info(f"--- E2E Test: Invalid symbol request PASSED ---")
            
                # Optional: Add test for malformed token if needed
                async def test_analysis_malformed_token(self):
                    """Tests behavior with a malformed token."""
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        headers = {"Authorization": "Bearer invalid.token.string"}
                        symbol = "GOOGL"
                        logger.info(f"--- E2E Test: Starting request with malformed token for {symbol} ---")
                        response = await client.get(f"/api/analyze/{symbol}", headers=headers)
            
                        logger.debug(f"Response Status Code: {response.status_code}")
                        logger.debug(f"Response Text: {response.text}")
            
                        assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                             f"Expected 401 Unauthorized for malformed token, got {response.status_code}"
                        assert "Could not validate credentials" in response.json().get("detail", "")
            
                        logger.info(f"--- E2E Test: Malformed token request PASSED ---")
            
            