import pytest
from backend.agents.categories import CategoryManager, CategoryType

@pytest.mark.asyncio
class TestCategoryIntegration:
    @pytest.fixture(scope="class") # Use class scope if CategoryManager is stateless
    def category_manager(self):
        """Fixture to provide a CategoryManager instance."""
        # Ensure any necessary environment or configuration for agents is set here if needed
        return CategoryManager()

    # Helper method to validate results structure consistently
    def _validate_agent_results(self, results, category_type):
        """Helper to validate the structure and content of agent results."""
        assert isinstance(results, list), f"Results for {category_type} should be a list"
        # Filter out any None or non-dict results returned by agents
        valid_results = [r for r in results if r is not None and isinstance(r, dict)]

        # Validate structure of each valid result
        for r in valid_results:
            assert "agent_name" in r, f"Agent result {r} missing 'agent_name'"
            assert isinstance(r["agent_name"], str), f"'agent_name' in result {r} should be a string"
            # Add more checks based on the expected output structure of your agents if needed

        return valid_results

    async def test_valuation_category(self, category_manager):
        """Test valuation category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.VALUATION, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.VALUATION)

        # Check for specific agents expected in this category
        assert any(r["agent_name"].startswith("pe_ratio") for r in valid_results), \
               f"Expected 'pe_ratio' agent result in {CategoryType.VALUATION.name} category output for {symbol}"
        assert any(r["agent_name"].startswith("peg_ratio") for r in valid_results), \
               f"Expected 'peg_ratio' agent result in {CategoryType.VALUATION.name} category output for {symbol}"

    async def test_technical_category(self, category_manager):
        """Test technical category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.TECHNICAL, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.TECHNICAL)
        assert len(valid_results) > 0, f"Expected at least one valid agent result dictionary for {CategoryType.TECHNICAL.name} category for {symbol}."

        # Check for specific agents expected in this category
        # Corrected check for RSI agent name (case-insensitive)
        has_rsi = any(r.get("agent_name", "").lower().startswith("rsi") for r in valid_results)
        has_macd = any(r.get("agent_name", "").lower().startswith("macd") for r in valid_results)

        assert has_rsi, f"Expected 'RSI' agent result in {CategoryType.TECHNICAL.name} category output for {symbol}"
        assert has_macd, f"Expected 'macd' agent result in {CategoryType.TECHNICAL.name} category output for {symbol}"

    async def test_market_category(self, category_manager):
        """Test market category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.MARKET, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.MARKET)

        # Check for specific agents expected in this category
        assert any(r["agent_name"].startswith("volatility") for r in valid_results), \
               f"Expected 'volatility' agent result in {CategoryType.MARKET.name} category output for {symbol}"
        assert any(r["agent_name"].startswith("correlation") for r in valid_results), \
               f"Expected 'correlation' agent result in {CategoryType.MARKET.name} category output for {symbol}"

    async def test_stealth_category(self, category_manager):
        """Test stealth category execution and expected agents."""
        symbol = "RELIANCE.NS"
        results = await category_manager.execute_category(
            CategoryType.STEALTH, symbol
        )

        valid_results = self._validate_agent_results(results, CategoryType.STEALTH)

        # Check for specific agents expected in this category
        assert any(r["agent_name"].startswith("moneycontrol") for r in valid_results), \
               f"Expected 'moneycontrol' agent result in {CategoryType.STEALTH.name} category output for {symbol}"

