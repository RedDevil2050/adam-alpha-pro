from backend.agents.valuation.base import ValuationAgentBase
from backend.utils.data_provider import fetch_price_point, fetch_eps
from loguru import logger

agent_name = "earnings_yield_agent"

class EarningsYieldAgent(ValuationAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            price_data = await fetch_price_point(symbol)
            current_price = price_data.get("latestPrice", 0)
            
            # Try to get EPS from agent outputs first
            eps = None
            if "eps_agent" in agent_outputs and agent_outputs["eps_agent"].get("value"):
                eps = float(agent_outputs["eps_agent"]["value"])
            else:
                eps = await fetch_eps(symbol)

            if not eps or not current_price or current_price <= 0:
                return self._error_response(symbol, "Missing price or EPS data")

            earnings_yield = (eps / current_price) * 100

            # Get market context for regime-aware thresholds
            market_context = await self.get_market_context(symbol)
            regime = market_context.get('regime', 'NEUTRAL')
            
            # Adjust thresholds based on regime
            thresholds = {
                'BULL': {'high': 8, 'low': 4},
                'BEAR': {'high': 12, 'low': 6},
                'NEUTRAL': {'high': 10, 'low': 5}
            }.get(regime, {'high': 10, 'low': 5})

            if earnings_yield > thresholds['high']:
                verdict = "ATTRACTIVE"
                confidence = self.adjust_for_market_regime(0.9, regime)
            elif earnings_yield > thresholds['low']:
                verdict = "FAIR"
                confidence = self.adjust_for_market_regime(0.6, regime)
            else:
                verdict = "EXPENSIVE"
                confidence = self.adjust_for_market_regime(0.3, regime)

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(earnings_yield, 2),
                "details": {
                    "current_price": current_price,
                    "eps": eps,
                    "yield_percent": round(earnings_yield, 2),
                    "market_regime": regime
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Earnings yield error: {e}")
            return self._error_response(symbol, str(e))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = EarningsYieldAgent()
    return await agent.execute(symbol, agent_outputs)
