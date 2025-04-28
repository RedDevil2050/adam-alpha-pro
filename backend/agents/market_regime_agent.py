from backend.utils.data_provider import fetch_price_series
from backend.agents.base import AgentBase
import pandas as pd

class MarketRegimeAgent(AgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict = None) -> dict:
        agent_name = self.__class__.__name__
        try:
            # Fetch historical price series
            price_data = await fetch_price_series(symbol, "2023-01-01", "2023-12-31")
            prices = pd.Series(price_data.get("prices", []))

            # Calculate market regime (example logic)
            volatility = prices.pct_change().std()
            trend = prices.pct_change().mean()

            if volatility > 0.02 and trend > 0:
                regime = "Bullish"
            elif volatility > 0.02 and trend < 0:
                regime = "Bearish"
            else:
                regime = "Neutral"

            return {
                "symbol": symbol,
                "verdict": regime,
                "confidence": min(volatility * 100, 100.0),
                "value": trend,
                "details": {"volatility": volatility, "trend": trend},
                "error": None,
                "agent_name": agent_name
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "verdict": "ERROR",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": str(e),
                "agent_name": agent_name
            }
