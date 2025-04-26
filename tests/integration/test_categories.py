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
        assert results
        assert any(r["agent_name"].startswith("rsi") for r in results)
        assert any(r["agent_name"].startswith("macd") for r in results)

    async def test_market_category(self, category_manager):
        """Test market category execution"""
        results = await category_manager.execute_category(
            CategoryType.MARKET, "RELIANCE.NS"
        )
        assert results
        assert any(r["agent_name"].startswith("market_regime") for r in results)

    async def test_stealth_category(self, category_manager):
        """Test stealth category execution"""
        results = await category_manager.execute_category(
            CategoryType.STEALTH, "RELIANCE.NS"
        )
        assert results
        assert any(r["agent_name"].startswith("moneycontrol") for r in results)

