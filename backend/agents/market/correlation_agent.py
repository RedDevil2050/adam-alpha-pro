from backend.utils.data_provider import fetch_price_series
from backend.config.settings import get_settings # Use get_settings
import numpy as np
import pandas as pd
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "correlation_agent"
AGENT_CATEGORY = "market" # Define category for the decorator

# Apply the decorator to the standalone run function
@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    # Core logic moved from the previous _execute method

    settings = get_settings()

    # Get price data for symbol and market index (Core Logic)
    symbol_prices = await fetch_price_series(symbol)
    # Use a default market index if not set in config
    market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL if hasattr(settings.data_provider, 'MARKET_INDEX_SYMBOL') else '^NSEI' # Example default
    market_prices = await fetch_price_series(market_symbol)

    min_days = 60 # Minimum required days
    if not symbol_prices or not market_prices or len(symbol_prices) < min_days or len(market_prices) < min_days:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price history for {symbol} or market index {market_symbol} (need {min_days} days)"},
            "agent_name": agent_name
        }

    # Calculate returns (Core Logic)
    sym_series = pd.Series(symbol_prices)
    mkt_series = pd.Series(market_prices)
    sym_ret = sym_series.pct_change().dropna()
    mkt_ret = mkt_series.pct_change().dropna()

    # Align returns (simple intersection)
    common_index = sym_ret.index.intersection(mkt_ret.index)
    if len(common_index) < min_days:
         return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient overlapping data points ({len(common_index)} < {min_days}) between {symbol} and {market_symbol}"},
            "agent_name": agent_name
        }
    sym_ret = sym_ret.loc[common_index]
    mkt_ret = mkt_ret.loc[common_index]

    # Ensure enough data points after alignment
    if len(sym_ret) < 30 or len(mkt_ret) < 30: # Need at least 30 for 30d correlation
         return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient aligned data points for 30d correlation ({len(sym_ret)} points)"},
            "agent_name": agent_name
        }

    # Calculate rolling correlations (Core Logic)
    # Use tail for recent data
    correlation_30d = sym_ret.tail(30).corr(mkt_ret.tail(30))
    correlation_60d = sym_ret.tail(60).corr(mkt_ret.tail(60)) if len(sym_ret) >= 60 else np.nan

    # Handle potential NaN correlations
    if np.isnan(correlation_30d):
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not calculate 30d correlation (NaN result)", "market_index": market_symbol},
            "agent_name": agent_name
        }

    # Calculate z-score of correlation change (Core Logic)
    # Z-score calculation needs a series of correlation changes, not just one change.
    # The original z-score logic seems flawed. Let's simplify the verdict logic based on current correlation levels.
    # Alternative: Calculate rolling correlation over a longer period and check recent deviation.

    # Simplified Verdict Logic based on 30d correlation
    if correlation_30d > 0.7:
        verdict = "HIGH_CORRELATION"
        confidence = 0.8 # Adjusted confidence
    elif correlation_30d < 0.3:
        verdict = "LOW_CORRELATION"
        confidence = 0.7 # Adjusted confidence
    else:
        verdict = "NORMAL_CORRELATION"
        confidence = 0.6

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(correlation_30d, 4), # 30d correlation as primary value
        "details": {
            "correlation_30d": round(correlation_30d, 4),
            "correlation_60d": round(correlation_60d, 4) if not np.isnan(correlation_60d) else None,
            # "correlation_zscore": round(corr_zscore, 2), # Removed flawed z-score
            "market_index_used": market_symbol
        },
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result

# Keep the class definition commented out or remove if no longer needed
# and MarketAgentBase is not providing other essential functionality.
# from backend.agents.market.base import MarketAgentBase
# class CorrelationAgent(MarketAgentBase):
#     async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
#         # ... logic moved to run() ...
#         pass
