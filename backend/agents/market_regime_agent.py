from backend.utils.data_provider import fetch_price_series
import pandas as pd
from backend.agents.decorators import standard_agent_execution

agent_name = "MarketRegimeAgent"
AGENT_CATEGORY = "market"

@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Analyze the market regime based on price series and volatility index.

    Args:
        symbol: Stock symbol
        agent_outputs: Optional outputs from other agents

    Returns:
        A dictionary containing the market regime analysis.
    """
    try:
        # Fetch data concurrently
        closes_task = fetch_price_series(symbol)
        vix_task = fetch_price_series("^VIX")
        closes, vix = await asyncio.gather(closes_task, vix_task)

        if closes is None or len(closes) < 260:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": "Insufficient data",
                "agent_name": agent_name,
            }

        # Calculate moving averages and slope
        series = pd.Series(closes)
        dma200 = series.rolling(200).mean()
        slope = (dma200.iloc[-1] - dma200.iloc[-21]) / dma200.iloc[-21]

        # Determine market regime
        if slope > 0.02:
            regime = "BULLISH"
        elif slope < -0.02:
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"

        return {
            "symbol": symbol,
            "verdict": regime,
            "confidence": round(abs(slope), 2),
            "value": slope,
            "details": {"dma200_slope": slope},
            "agent_name": agent_name,
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"error": str(e)},
            "agent_name": agent_name,
        }
