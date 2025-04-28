from typing import List
from backend.agents.valuation.base import ValuationAgent

class PERatioAgent(ValuationAgent):
    def get_dependencies(self) -> List[str]:
        return ["eps_agent"]

    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            price_data = await fetch_price_point(symbol)
            current_price = price_data.get("latestPrice", 0)

            eps = None
            if "eps_agent" in agent_outputs:
                eps = float(agent_outputs["eps_agent"]["value"])
            else:
                eps = await fetch_eps(symbol)

            if not eps or eps <= 0 or not current_price:
                return self._error_response(symbol, "Invalid data")

            market_context = await self.get_market_context(symbol)
            adjustments = self.get_regime_adjustments(market_context.get('regime', 'NEUTRAL'))
            
            pe_ratio = current_price / eps * adjustments['multiplier']
            verdict = self._get_verdict(pe_ratio, adjustments)
            confidence = self._calculate_confidence(pe_ratio, adjustments)

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(pe_ratio, 2),
                "details": {
                    "current_price": current_price,
                    "eps": eps,
                    "market_regime": market_context.get('regime')
                },
                "error": None,
                "agent_name": self.__class__.__name__
            }

        except Exception as e:
            return self._error_response(symbol, str(e))

    def _get_verdict(self, pe_ratio: float, thresholds: dict) -> str:
        if pe_ratio < thresholds['low']:
            return "BUY"
        elif pe_ratio < thresholds['high']:
            return "HOLD"
        return "AVOID"

    def _calculate_confidence(self, pe_ratio: float, thresholds: dict) -> float:
        base_confidence = max(0.0, 100.0 - min(pe_ratio, 50.0) * 2)
        return self.adjust_for_market_regime(base_confidence/100, 
                                          market_context.get('regime', 'NEUTRAL'))

# For backwards compatibility
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = PERatioAgent()
    return await agent.execute(symbol, agent_outputs)
