import pytest
from backend.agents.categories import CategoryManager, CategoryType # Assuming CategoryType is an Enum

# Note: If CategoryManager relies on specific environment variables or external
# dependencies that need mocking or setup, ensure that setup happens before tests run.
# For example, mocking database connections, external APIs, etc.

@pytest.mark.asyncio
class TestCategoryIntegration:
    @pytest.fixture(scope="class") # Use class scope if CategoryManager is stateless and creation is non-trivial
    def category_manager(self):
        """Fixture to provide a CategoryManager instance."""
        # Any setup specific to initializing CategoryManager or its dependencies
        # for testing should happen here or in conftest.py
        return CategoryManager()

    # Helper method to validate results structure consistently
    def _validate_agent_results(self, results, category_type: CategoryType):
        """Helper to validate the structure and content of agent results."""
        # The manager should always return a list, even if empty or filled with None
        assert isinstance(results, list), f"Results for {category_type.name} should be a list"

        # Filter out any None or non-dict results returned by potentially failing agents
        valid_results = [r for r in results if isinstance(r, dict)]

        # Validate structure of each valid result dictionary
        for r in valid_results:
            assert "agent_name" in r, f"Agent result {r} from {category_type.name} missing 'agent_name' key"
            assert isinstance(r["agent_name"], str), f"'agent_name' in result {r} from {category_type.name} should be a string"
            # Add more checks based on the expected *common* output structure of your agents if needed
            # e.g., assert 'value' in r, f"Result {r} missing 'value'"
            # e.g., assert 'verdict' in r, f"Result {r} missing 'verdict'"


        # Note: This helper *doesn't* assert that valid_results is non-empty.
        # Individual tests can add asserts like `assert len(valid_results) > 0`
        # if the specific category is expected to always produce results.

        return valid_results

    async def test_valuation_category(self, category_manager):
        """Test valuation category execution and expected agents."""
        symbol = "RELIANCE.NS" # Use a symbol likely to have data relevant for agents
        results = await category_manager.execute_category(
            CategoryType.VALUATION, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.VALUATION)

        # Assert that at least the specifically expected agents produced valid results
        assert any(r["agent_name"].startswith("pe_ratio") for r in valid_results), \
               f"Expected 'pe_ratio' agent result in {CategoryType.VALUATION.name} category output for {symbol}"
        assert any(r["agent_name"].startswith("peg_ratio") for r in valid_results), \
               f"Expected 'peg_ratio' agent result in {CategoryType.VALUATION.name} category output for {symbol}"
        # Add assertions for other specific valuation agents if expected


    async def test_technical_category(self, category_manager):
        """Test technical category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.TECHNICAL, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.TECHNICAL)

        # Assert that *some* technical agent produced a valid result.
        # Remove or adjust if this category can validly return an empty list of valid results.
        assert len(valid_results) > 0, f"Expected at least one valid agent result dictionary for {CategoryType.TECHNICAL.name} category for {symbol}."

        # Check for specific agents expected in this category
        # Use r["agent_name"] directly as _validate_agent_results ensures it exists
        has_rsi = any(r["agent_name"].startswith("rsi") for r in valid_results)
        has_macd = any(r["agent_name"].startswith("macd") for r in valid_results)
        # Add assertions for other specific technical agents if expected

        assert has_rsi, f"Expected 'rsi' agent result in {CategoryType.TECHNICAL.name} category output for {symbol}"
        assert has_macd, f"Expected 'macd' agent result in {CategoryType.TECHNICAL.name} category output for {symbol}"


    async def test_market_category(self, category_manager):
        """Test market category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.MARKET, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.MARKET)

        # Check for specific agents expected in this category
        # Use r["agent_name"] directly as _validate_agent_results ensures it exists
        assert any(r["agent_name"].startswith("volatility") for r in valid_results), \
               f"Expected 'volatility' agent result in {CategoryType.MARKET.name} category output for {symbol}"
        assert any(r["agent_name"].startswith("correlation") for r in valid_results), \
               f"Expected 'correlation' agent result in {CategoryType.MARKET.name} category output for {symbol}"
        # Add assertions for other specific market agents if expected


    async def test_stealth_category(self, category_manager):
        """Test stealth category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.STEALTH, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.STEALTH)

        # Check for specific agents expected in this category
        # Use r["agent_name"] directly as _validate_agent_results ensures it exists
        assert any(r["agent_name"].startswith("moneycontrol") for r in valid_results), \
               f"Expected 'moneycontrol' agent result in {CategoryType.STEALTH.name} category output for {symbol}"
        # Add assertions for other specific stealth agents if expected

    # Optional: Add tests for error handling, e.g.:
    # - What happens if an individual agent raises an unhandled exception?
    # - What happens if all agents in a category return None or fail?
    # async def test_category_with_failing_agents(self, category_manager):
    #     """Test execution when some or all agents in a category fail."""
    #     # This would likely involve mocking the individual agent `run` functions
    #     # to return None or raise exceptions to simulate failure scenarios.
    #     pass

    # async def test_category_with_no_agents_registered(self, category_manager):
    #     """Test execution of a CategoryType for which no agents are registered."""
    #     # This depends on your CategoryManager's internal structure and how it
    #     # handles CategoryTypes with no associated agents. It should likely
    #     # return an empty list [] or raise a specific error.
    #     pass
