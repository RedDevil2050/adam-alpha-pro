from backend.agents.technical.base import TechnicalAgent
# Correct the import path
from backend.utils.data_provider import fetch_ohlcv_series


class RSIAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            df = await fetch_ohlcv_series(symbol)
            if df is None or df.empty:
                return self._error_response(symbol, "No data available")

            market_context = await self.get_market_context(symbol)
            volatility = market_context.get("volatility", 0.2)
            adjustments = self.get_volatility_adjustments(volatility)

            rsi = self._calculate_rsi(
                df["close"], period=int(14 * adjustments["period_adj"])
            )

            # Adjust signals based on market regime
            signals = self._get_regime_signals(
                rsi, market_context.get("regime", "NEUTRAL")
            )

            return {
                "symbol": symbol,
                "verdict": signals["verdict"],
                "confidence": signals["confidence"],
                "value": round(rsi, 2),
                "details": {
                    "rsi": round(rsi, 2),
                    "market_regime": market_context.get("regime"),
                },
                "error": None,
                "agent_name": self.__class__.__name__,
            }

        except Exception as e:
            return self._error_response(symbol, str(e))

    def _get_regime_signals(self, rsi: float, regime: str) -> dict:
        base_oversold = 30
        base_overbought = 70

        regime_adjustments = {
            "BULL": {"oversold": 35, "overbought": 75},
            "BEAR": {"oversold": 25, "overbought": 65},
            "VOLATILE": {"oversold": 20, "overbought": 80},
        }

        levels = regime_adjustments.get(
            regime, {"oversold": base_oversold, "overbought": base_overbought}
        )

        if rsi < levels["oversold"]:
            return {
                "verdict": "BUY",
                "confidence": self.adjust_for_market_regime(0.8, regime),
            }
        elif rsi > levels["overbought"]:
            return {
                "verdict": "SELL",
                "confidence": self.adjust_for_market_regime(0.8, regime),
            }
        return {"verdict": "HOLD", "confidence": 0.5}


# For backwards compatibility
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = RSIAgent()
    return await agent.execute(symbol, agent_outputs)
