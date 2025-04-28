import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.config.settings import get_settings # Use get_settings()
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "beta_agent"
AGENT_CATEGORY = "risk" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str) -> dict:
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    settings = get_settings() # Get settings instance

    # Fetch price series for symbol and market index (Core Logic)
    symbol_prices = await fetch_price_series(symbol)
    # Use a default market index if not set in config
    market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL if hasattr(settings.data_provider, 'MARKET_INDEX_SYMBOL') else '^NSEI' # Example default
    market_prices = await fetch_price_series(market_symbol)

    # Validate data length (Core Logic)
    if not symbol_prices or not market_prices or len(symbol_prices) < 2 or len(market_prices) < 2:
        # Return NO_DATA format (decorator won't cache this)
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price data for {symbol} or market index {market_symbol}"},
            "agent_name": agent_name # Decorator might overwrite this, but good practice
        }

    # Calculate returns (Core Logic)
    # Ensure consistent indexing if lengths differ slightly (e.g., align dates)
    sym_series = pd.Series(symbol_prices) # Assuming prices are just values; if dicts/tuples with dates, adjust
    mkt_series = pd.Series(market_prices)
    # A more robust approach would align based on dates if available
    sym_ret = sym_series.pct_change().dropna()
    mkt_ret = mkt_series.pct_change().dropna()

    # Align returns if necessary (simple intersection for now)
    common_index = sym_ret.index.intersection(mkt_ret.index)
    if len(common_index) < 2:
         return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient overlapping data points between {symbol} and {market_symbol}"},
            "agent_name": agent_name
        }
    sym_ret = sym_ret.loc[common_index]
    mkt_ret = mkt_ret.loc[common_index]


    # Beta calculation (Core Logic)
    # Check for zero variance in market returns
    mkt_var = mkt_ret.var()
    if mkt_var == 0:
        beta = np.nan # Or handle as appropriate (e.g., 1.0 or specific verdict)
    else:
        beta = float(sym_ret.cov(mkt_ret) / mkt_var)

    # Value at Risk (VaR) calculation (Core Logic)
    confidence_level = 0.95
    var = float(np.percentile(sym_ret, (1 - confidence_level) * 100)) if not sym_ret.empty else np.nan

    # Sharpe Ratio (Core Logic)
    risk_free = settings.data_provider.RISK_FREE_RATE if hasattr(settings.data_provider, 'RISK_FREE_RATE') else 0.04 # Example default
    excess_ret = sym_ret - risk_free/252  # Daily adjustment
    std_dev_excess = excess_ret.std()
    if std_dev_excess == 0 or excess_ret.empty:
        sharpe = 0.0 # Or handle as appropriate
    else:
        sharpe = float(np.sqrt(252) * excess_ret.mean() / std_dev_excess)

    # Correlation analysis (Core Logic)
    correlation = float(sym_ret.corr(mkt_ret)) if not sym_ret.empty and not mkt_ret.empty else np.nan

    # Risk scoring based on multiple metrics (Core Logic)
    # Handle potential NaN values from calculations
    beta_score = max(0, 1 - abs(beta - 1)) if not np.isnan(beta) else 0
    var_score = max(0, 1 + var/0.05) if not np.isnan(var) else 0 # Normalize VaR
    sharpe_score = min(1, max(0, sharpe/3)) if not np.isnan(sharpe) else 0

    composite_score = (beta_score * 0.4 + var_score * 0.3 + sharpe_score * 0.3)

    if composite_score > 0.7:
        verdict = "LOW_RISK"
    elif composite_score > 0.4:
        verdict = "MODERATE_RISK"
    else:
        verdict = "HIGH_RISK"

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(composite_score * 100, 2), # Use composite score for confidence
        "value": round(beta, 4) if not np.isnan(beta) else None, # Beta as primary value
        "details": {
            "beta": round(beta, 4) if not np.isnan(beta) else None,
            "value_at_risk_95": round(var * 100, 2) if not np.isnan(var) else None, # Specify confidence level
            "sharpe_ratio": round(sharpe, 2) if not np.isnan(sharpe) else None,
            "market_correlation": round(correlation, 2) if not np.isnan(correlation) else None,
            "market_index_used": market_symbol,
            "risk_scores": {
                "beta_component": round(beta_score, 2),
                "var_component": round(var_score, 2),
                "sharpe_component": round(sharpe_score, 2)
            }
        },
        "score": round(composite_score, 4), # Keep composite score if needed elsewhere
        "agent_name": agent_name # Decorator might overwrite this
    }

    # Decorator handles caching and tracker update
    return result
