from backend.agents.valuation.base import ValuationAgentBase
from backend.utils.data_provider import fetch_price_point, fetch_dividend
from loguru import logger

agent_name = "dividend_yield_agent"

class DividendYieldAgent(ValuationAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            price_data = await fetch_price_point(symbol)
            current_price = price_data.get("latestPrice", 0)
            annual_dividend = await fetch_dividend(symbol)

            if not annual_dividend or not current_price or current_price <= 0:
                return self._error_response(symbol, "Missing price or dividend data")

            dividend_yield = (annual_dividend / current_price) * 100

            # Score based on dividend yield ranges
            if dividend_yield > 6:
                verdict = "HIGH_YIELD"
                confidence = 0.9
            elif dividend_yield > 3:
                verdict = "ATTRACTIVE_YIELD"
                confidence = 0.7
            elif dividend_yield > 1:
                verdict = "MODERATE_YIELD"
                confidence = 0.5
            else:
                verdict = "LOW_YIELD"
                confidence = 0.3

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(dividend_yield, 2),
                "details": {
                    "current_price": current_price,
                    "annual_dividend": annual_dividend,
                    "yield_percent": round(dividend_yield, 2)
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Dividend yield error: {e}")
            return self._error_response(symbol, str(e))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = DividendYieldAgent()
    return await agent.execute(symbol, agent_outputs)
