from backend.utils.data_provider import fetch_price_series, fetch_volume_series
import numpy as np
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "liquidity_agent"
AGENT_CATEGORY = "market" # Define category for the decorator

# Apply the decorator to the standalone run function
@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    # Core logic moved from the previous _execute method

    # Get price and volume data (Core Logic)
    # Consider fetching OHLCV data if available for a better spread proxy
    prices = await fetch_price_series(symbol)
    volumes = await fetch_volume_series(symbol)

    min_days = 20 # Minimum required days for average volume
    if not prices or not volumes or len(prices) < min_days or len(volumes) < min_days:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price or volume data for {symbol} (need {min_days} days)"},
            "agent_name": agent_name
        }

    # Ensure consistent lengths (use tail)
    common_length = min(len(prices), len(volumes))
    prices = prices[-common_length:]
    volumes = volumes[-common_length:]

    if common_length < min_days:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient aligned price/volume data ({common_length} < {min_days})"},
            "agent_name": agent_name
        }

    # Calculate liquidity metrics (Core Logic)
    prices_arr = np.array(prices)
    volumes_arr = np.array(volumes)

    avg_daily_volume_20d = np.mean(volumes_arr[-min_days:])
    last_volume = volumes_arr[-1]
    last_price = prices_arr[-1]

    # Avoid division by zero for avg_daily_volume
    if avg_daily_volume_20d == 0:
        relative_volume = np.inf # Or handle as zero liquidity
        liquidity_score = 0.0 # Assign lowest score if avg volume is zero
    else:
        relative_volume = last_volume / avg_daily_volume_20d
        # Simple liquidity score based on relative volume (needs refinement)
        # Cap relative volume contribution to score
        volume_score = min(1.0, relative_volume / 3.0) # e.g., 3x avg volume gives max score
        liquidity_score = volume_score # Simplified score based only on volume for now

    turnover = last_volume * last_price

    # Removed spread_proxy calculation as fetch_price_series likely only provides close prices.
    # A proper spread calculation requires High and Low prices.
    # spread_proxy = np.mean([(h-l)/c for h,l,c in zip(prices[-5:], prices[-5:], prices[-5:])]) # Incorrect usage
    # spread_score = max(0.0, 1 - spread_proxy*10)
    # liquidity_score = (volume_score + spread_score) / 2 # Adjusted score calculation

    # Verdict based on liquidity score (Core Logic)
    if liquidity_score > 0.7:
        verdict = "HIGH_LIQUIDITY"
        confidence = 0.8 # Adjusted confidence
    elif liquidity_score > 0.3:
        verdict = "MODERATE_LIQUIDITY"
        confidence = 0.6
    else:
        verdict = "LOW_LIQUIDITY"
        confidence = 0.4 # Adjusted confidence

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(liquidity_score, 4), # Liquidity score as primary value
        "details": {
            "avg_daily_volume_20d": int(avg_daily_volume_20d),
            "last_volume": int(last_volume),
            "relative_volume_vs_20d_avg": round(relative_volume, 2) if avg_daily_volume_20d != 0 else None,
            "last_turnover": int(turnover),
            # "spread_proxy": round(spread_proxy, 4) # Removed
        },
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result

# Keep the class definition commented out or remove if no longer needed.
# from backend.agents.market.base import MarketAgentBase
# class LiquidityAgent(MarketAgentBase):
#     async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
#         # ... logic moved to run() ...
#         pass
