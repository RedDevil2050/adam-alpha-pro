from backend.agents.valuation.base import ValuationAgentBase
from backend.utils.data_provider import fetch_price_point, fetch_fcf_per_share
from loguru import logger

agent_name = "reverse_dcf_agent"

class ReverseDCFAgent(ValuationAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            price_data = await fetch_price_point(symbol)
            current_price = price_data.get("latestPrice", 0)
            fcf = await fetch_fcf_per_share(symbol)

            if not fcf or fcf <= 0 or not current_price:
                return self._error_response(symbol, "Missing data")

            # Implied growth rate calculation
            discount_rate = 0.10  # 10% discount rate
            terminal_multiple = 15
            years = 10

            # Calculate implied growth rate using binary search
            low, high = -0.2, 0.5  # -20% to +50% growth
            while high - low > 0.001:
                mid = (low + high) / 2
                dcf_value = self._calculate_dcf(fcf, mid, discount_rate, years, terminal_multiple)
                
                if abs(dcf_value - current_price) < 0.01:
                    implied_growth = mid
                    break
                elif dcf_value > current_price:
                    high = mid
                else:
                    low = mid
            else:
                implied_growth = (low + high) / 2

            # Score reasonableness of implied growth
            if implied_growth > 0.3:
                verdict = "AGGRESSIVE"
                confidence = 0.3
            elif implied_growth > 0.15:
                verdict = "MODERATE"
                confidence = 0.6
            elif implied_growth > 0:
                verdict = "REASONABLE" 
                confidence = 0.9
            else:
                verdict = "DECLINE"
                confidence = 0.4

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(implied_growth * 100, 2),
                "details": {
                    "implied_growth_rate": round(implied_growth * 100, 2),
                    "current_price": current_price,
                    "fcf_per_share": fcf
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Reverse DCF error: {e}")
            return self._error_response(symbol, str(e))

    def _calculate_dcf(self, fcf: float, growth: float, discount: float, years: int, terminal_mult: float) -> float:
        value = 0
        current_fcf = fcf
        
        for _ in range(years):
            current_fcf *= (1 + growth)
            value += current_fcf / ((1 + discount) ** (_ + 1))
            
        terminal_value = current_fcf * terminal_mult / ((1 + discount) ** years)
        return value + terminal_value

# For backwards compatibility
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = ReverseDCFAgent()
    return await agent.execute(symbol, agent_outputs)
