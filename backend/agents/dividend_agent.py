from backend.utils.data_provider import fetch_price_point
from backend.config.settings import settings

async def run(symbol: str, agent_outputs: dict = None) -> dict:
    agent_name = "dividend_agent"
    try:
        price = await fetch_price_point(symbol)
        dividend_yield = settings.DIVIDEND_YIELD if hasattr(settings, 'DIVIDEND_YIELD') else 0.02
        value = dividend_yield
        verdict = "BUY" if dividend_yield*price > 1 else "HOLD"
        confidence = min(dividend_yield*100, 100.0)
        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": value,
            "details": {"dividend_yield": dividend_yield},
            "error": None,
            "agent_name": agent_name
        }
    except Exception as e:
        return {"symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
                "details": {}, "error": str(e), "agent_name": agent_name}
