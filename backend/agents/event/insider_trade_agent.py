import httpx
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import tracker
# Import the specific data provider function
from backend.utils.data_provider import fetch_insider_trades

agent_name = "insider_trade_agent"


async def run(symbol: str) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch insider trade data using the data_provider function
    trades = []
    error_message = None
    try:
        # Use the imported fetch function
        # Assuming fetch_insider_trades returns a list of trade dicts or None/empty list
        trades_data = await fetch_insider_trades(symbol)
        trades = trades_data if isinstance(trades_data, list) else []

    except Exception as e:
        error_message = str(e)
        # Return error structure if fetch fails
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"error": error_message},
            "error": error_message, # Keep top-level error for consistency
            "agent_name": agent_name,
        }

    # Always include the 'insider_trades' key
    if not trades:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": 0,
            "details": {},
            "insider_trades": [], # Ensure key exists even if empty
            "agent_name": agent_name,
        }
    else:
        # Score based on number of trades
        count = len(trades)
        score = min(count / 10.0, 1.0)
        verdict = (
            "ACTIVE" if score >= 0.6 else "MODERATE" if score >= 0.3 else "INACTIVE"
        )
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": count,
            "details": {"trades_count": count}, # Avoid returning large list of trades
            "insider_trades": trades, # Include trades if present (consider limiting size if needed)
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
