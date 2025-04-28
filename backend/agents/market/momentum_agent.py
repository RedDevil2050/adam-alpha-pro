from backend.utils.data_provider import fetch_price_series, fetch_volume_series
import numpy as np
import pandas as pd
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "momentum_agent"
AGENT_CATEGORY = "market"  # Define category for the decorator


# Apply the decorator to the standalone run function
@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(
    symbol: str, agent_outputs: dict = None
) -> dict:  # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    # Core logic moved from the previous _execute method

    # Fetch price and volume data (Core Logic)
    prices = await fetch_price_series(symbol)
    volumes = await fetch_volume_series(symbol)

    min_days = 120  # Minimum required days for longest momentum period
    if not prices or not volumes or len(prices) < min_days or len(volumes) < min_days:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Insufficient price or volume data for {symbol} (need {min_days} days)"
            },
            "agent_name": agent_name,
        }

    # Ensure consistent lengths (use tail)
    common_length = min(len(prices), len(volumes))
    prices = prices[-common_length:]
    volumes = volumes[-common_length:]

    if common_length < min_days:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Insufficient aligned price/volume data ({common_length} < {min_days})"
            },
            "agent_name": agent_name,
        }

    # Calculate momentum metrics (Core Logic)
    prices_arr = np.array(prices)
    volumes_arr = np.array(volumes)

    # Calculate log returns for momentum calculation (more stable than pct_change)
    log_returns = np.diff(np.log(prices_arr))
    if len(log_returns) < min_days - 1:  # Need enough returns for the periods
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Insufficient returns data after calculation ({len(log_returns)} points)"
            },
            "agent_name": agent_name,
        }

    # Multiple timeframe momentum (sum of log returns)
    mom_20 = np.sum(log_returns[-20:])
    mom_60 = np.sum(log_returns[-60:])
    mom_120 = np.sum(log_returns[-120:])

    # Volume trend (avoid division by zero)
    avg_vol_60 = np.mean(volumes_arr[-60:])
    if avg_vol_60 == 0:
        vol_trend = 0.0  # Or handle as undefined
    else:
        avg_vol_20 = np.mean(volumes_arr[-20:])
        vol_trend = (avg_vol_20 / avg_vol_60) - 1

    # Composite momentum score (Core Logic)
    weights = [0.5, 0.3, 0.2]  # Higher weight to recent momentum
    raw_momentum_score = (
        weights[0] * mom_20 + weights[1] * mom_60 + weights[2] * mom_120
    )
    # Adjust score by volume trend (amplify if volume increases, dampen if decreases)
    # Use max(0, ...) to avoid negative volume trend excessively penalizing
    volume_adjustment = 1 + max(0, vol_trend)  # Simple adjustment, could be refined
    momentum_score = raw_momentum_score * volume_adjustment

    # Market regime adjustment (Simplified/Placeholder)
    # The original code called self.get_market_context and self.adjust_for_market_regime.
    # These are not available in the standalone function without the class structure or importing them.
    # Option 1: Assume market regime comes from agent_outputs if needed.
    # Option 2: Remove regime adjustment for now.
    # Let's remove it for this refactoring pass.
    market_regime = (
        agent_outputs.get("market_regime_agent", {}).get("verdict")
        if agent_outputs
        else "UNKNOWN"
    )
    # confidence_adjustment = 1.0 # Placeholder, implement adjustment logic if needed

    # Generate verdict based on momentum score (Core Logic)
    # Thresholds might need tuning based on log return sums
    if momentum_score > 0.08:  # Adjusted threshold for log returns
        verdict = "STRONG_MOMENTUM"
        confidence = 0.9
    elif momentum_score > 0.03:  # Adjusted threshold
        verdict = "POSITIVE_MOMENTUM"
        confidence = 0.7
    elif momentum_score > -0.03:  # Adjusted threshold
        verdict = "NEUTRAL_MOMENTUM"
        confidence = 0.5
    elif momentum_score > -0.08:  # Adjusted threshold
        verdict = "NEGATIVE_MOMENTUM"
        confidence = 0.7
    else:
        verdict = "WEAK_MOMENTUM"
        confidence = 0.9

    # Apply confidence adjustment based on regime if implemented
    # confidence *= confidence_adjustment
    # confidence = round(max(0.1, min(0.9, confidence)), 4) # Clamp confidence

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(momentum_score, 4),  # Composite score as primary value
        "details": {
            "momentum_20d_logret_sum": round(mom_20, 4),
            "momentum_60d_logret_sum": round(mom_60, 4),
            "momentum_120d_logret_sum": round(mom_120, 4),
            "volume_trend_20d_vs_60d": round(vol_trend, 4),
            "market_regime_input": market_regime,  # Indicate regime used (if any)
        },
        "agent_name": agent_name,
    }

    # Decorator handles caching and tracker update
    return result


# Keep the class definition commented out or remove if no longer needed.
# from backend.agents.market.base import MarketAgentBase
# class MomentumAgent(MarketAgentBase):
#     async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
#         # ... logic moved to run() ...
#         pass
#
#     async def get_market_context(self, symbol: str) -> dict:
#         # This logic needs to be handled elsewhere or passed in
#         return {}
#
#     def adjust_for_market_regime(self, base_confidence: float, regime: str) -> float:
#         # This logic needs to be handled elsewhere or passed in
#         return base_confidence
