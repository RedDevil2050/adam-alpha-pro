import pytest
from backend.agents.categories import CategoryManager, CategoryType

@pytest.mark.asyncio
class TestCategoryIntegration:
    @pytest.fixture
    def category_manager(self):
        return CategoryManager()

    async def test_valuation_category(self, category_manager):
        """Test valuation category execution"""
        results = await category_manager.execute_category(
            CategoryType.VALUATION, "RELIANCE.NS"
        )
        assert results
        assert any(r["agent_name"].startswith("pe_ratio") for r in results)
        assert any(r["agent_name"].startswith("peg_ratio") for r in results)

    async def test_technical_category(self, category_manager):
        """Test technical category execution"""
        results = await category_manager.execute_category(
            CategoryType.TECHNICAL, "RELIANCE.NS"
        )
        assert results is not None, "Category execution should return a list, not None."
        assert len(results) > 0, "Technical category should execute at least one agent."
        
        # Filter out potential None results before checking agent names
        valid_results = [r for r in results if r is not None and isinstance(r, dict)]
        assert len(valid_results) > 0, "Expected at least one valid agent result dictionary."

        # Check for specific agent results
        has_rsi = any(r.get("agent_name", "").startswith("rsi") for r in valid_results)
        has_macd = any(r.get("agent_name", "").startswith("macd") for r in valid_results)
        
        assert has_rsi, "Expected RSI agent result in technical category output."
        assert has_macd, "Expected MACD agent result in technical category output."

    async def test_market_category(self, category_manager):
        """Test market category execution"""
        results = await category_manager.execute_category(
            CategoryType.MARKET, "RELIANCE.NS"
        )
        assert results, "Market category should return results"
        # Check for specific market agents like volatility or correlation
        assert any(r["agent_name"].startswith("volatility") for r in results if r), "Volatility agent result expected"
        assert any(r["agent_name"].startswith("correlation") for r in results if r), "Correlation agent result expected"

    async def test_stealth_category(self, category_manager):
        """Test stealth category execution"""
        results = await category_manager.execute_category(
            CategoryType.STEALTH, "RELIANCE.NS"
        )
        assert results
        assert any(r["agent_name"].startswith("moneycontrol") for r in results)

