import pandas as pd
import numpy as np
import logging  # Import the logging module
from backend.utils.data_provider import fetch_price_series
from backend.config.settings import get_settings  # Use get_settings()
from backend.agents.decorators import standard_agent_execution  # Import decorator

# Set up logging
logger = logging.getLogger(__name__)

agent_name = "beta_agent"
AGENT_CATEGORY = "risk"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates various risk metrics for a given stock symbol relative to a market index.

    Purpose:
        Evaluates the systematic risk (Beta), downside risk (VaR), risk-adjusted return (Sharpe Ratio),
        and correlation of a stock compared to the broader market. It computes a composite risk score
        based on these metrics and assigns a risk verdict (LOW_RISK, MODERATE_RISK, HIGH_RISK).

    Metrics Calculated:
        - Beta: Measures the volatility of the stock relative to the market index.
        - Value at Risk (VaR): Estimates the potential loss in value of the stock over a defined period
          for a given confidence interval (e.g., 95%). Reported as a negative percentage.
        - Sharpe Ratio: Measures the risk-adjusted return, considering the excess return over the
          risk-free rate per unit of volatility.
        - Correlation: Measures the linear relationship between the stock's returns and the market's returns.
        - Composite Risk Score: A weighted average of normalized scores derived from Beta, VaR, and Sharpe Ratio.

    Logic:
        1. Fetches historical price series for the stock symbol and the configured market index.
        2. Calculates daily percentage returns for both series.
        3. Aligns the return series to ensure calculations are based on overlapping periods.
        4. Calculates Beta using the covariance of stock/market returns divided by market return variance.
        5. Calculates VaR using the percentile of the stock's return distribution based on the configured confidence level.
        6. Calculates the Sharpe Ratio using the mean excess return over the risk-free rate, adjusted for volatility and annualized.
        7. Calculates the Pearson correlation coefficient between stock and market returns.
        8. Normalizes Beta, VaR, and Sharpe Ratio into scores between 0 and 1.
        9. Computes a composite score using configured weights for each normalized metric.
        10. Assigns a verdict (LOW_RISK, MODERATE_RISK, HIGH_RISK) based on configured thresholds applied to the composite score.

    Dependencies:
        - Requires historical price data for both the target symbol and the market index symbol.
        - Relies on `fetch_price_series` utility.

    Configuration Used (from settings.py):
        - `data_provider.MARKET_INDEX_SYMBOL`: The symbol for the market index (e.g., '\^NSEI').
        - `data_provider.RISK_FREE_RATE`: The annualized risk-free rate used for Sharpe Ratio calculation.
        - `agent_settings.beta.VAR_CONFIDENCE_LEVEL`: The confidence level for VaR calculation (e.g., 0.95 for 95%).
        - `agent_settings.beta.SHARPE_ANNUALIZATION_FACTOR`: The number of trading days in a year (e.g., 252) used for Sharpe Ratio annualization.
        - `agent_settings.beta.COMPOSITE_WEIGHT_*`: Weights for Beta, VaR, and Sharpe components in the composite score.
        - `agent_settings.beta.VERDICT_THRESHOLD_*`: Thresholds for classifying the composite score into LOW, MODERATE, or HIGH risk.

    Returns:
        dict: A dictionary containing the analysis results, including:
            - symbol (str): The input stock symbol.
            - verdict (str): 'LOW_RISK', 'MODERATE_RISK', 'HIGH_RISK', 'NO_DATA', or 'ERROR'.
            - confidence (float): The composite risk score (0-100).
            - value (float | None): The calculated Beta value.
            - details (dict): Contains the individual calculated metrics (beta, VaR, sharpe_ratio, market_correlation),
              the component scores used for the composite calculation, and the configuration values used during the run.
            - error (str | None): Error message if execution failed.
            - agent_name (str): The name of the agent ('beta_agent').
    """
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    settings = get_settings()  # Get settings instance
    beta_settings = settings.agent_settings.beta  # Access beta-specific settings

    # Fetch price series for symbol and market index (Core Logic)
    symbol_prices = await fetch_price_series(symbol)
    # Use market index from config
    market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL
    market_prices = await fetch_price_series(market_symbol)

    # Validate data length (Core Logic)
    if (
        symbol_prices is None or symbol_prices.empty
        or market_prices is None or market_prices.empty
        or len(symbol_prices) < 2
        or len(market_prices) < 2
    ):
        # Return NO_DATA format (decorator won't cache this)
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Insufficient price data for {symbol} or market index {market_symbol}"
            },
            "agent_name": agent_name,  # Decorator might overwrite this, but good practice
        }

    # Calculate returns (Core Logic)
    # Handle 2D price arrays by extracting the closing price column
    try:
        # Check if symbol_prices is a 2D array and extract closing prices
        if isinstance(symbol_prices, np.ndarray) and len(symbol_prices.shape) > 1:
            close_idx = 3  # Assuming 4th column (index 3) is close price
            sym_series = pd.Series(symbol_prices[:, close_idx])
        else:
            sym_series = pd.Series(symbol_prices)
            
        # Similarly for market prices
        if isinstance(market_prices, np.ndarray) and len(market_prices.shape) > 1:
            close_idx = 3  # Assuming 4th column (index 3) is close price
            mkt_series = pd.Series(market_prices[:, close_idx])
        else:
            mkt_series = pd.Series(market_prices)
            
        # A more robust approach would align based on dates if available
        sym_ret = sym_series.pct_change().dropna()
        mkt_ret = mkt_series.pct_change().dropna()
    except Exception as e:
        logger.error(f"Error processing price data in beta_agent: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Failed to process price data: {str(e)}"},
            "agent_name": agent_name,
        }

    # Align returns if necessary (simple intersection for now)
    common_index = sym_ret.index.intersection(mkt_ret.index)
    if len(common_index) < 2:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Insufficient overlapping data points between {symbol} and {market_symbol}"
            },
            "agent_name": agent_name,
        }
    sym_ret = sym_ret.loc[common_index]
    mkt_ret = mkt_ret.loc[common_index]

    # Beta calculation (Core Logic)
    # Check for zero variance in market returns
    mkt_var = mkt_ret.var()
    if mkt_var == 0:
        beta = np.nan  # Or handle as appropriate (e.g., 1.0 or specific verdict)
    else:
        beta = float(sym_ret.cov(mkt_ret) / mkt_var)

    # Value at Risk (VaR) calculation (Core Logic)
    confidence_level = beta_settings.VAR_CONFIDENCE_LEVEL  # Use setting
    var = (
        float(np.percentile(sym_ret, (1 - confidence_level) * 100))
        if not sym_ret.empty
        else np.nan
    )

    # Sharpe Ratio (Core Logic)
    risk_free = settings.data_provider.RISK_FREE_RATE  # Use setting
    annualization_factor = beta_settings.SHARPE_ANNUALIZATION_FACTOR  # Use setting
    excess_ret = (
        sym_ret - risk_free / annualization_factor
    )  # Daily adjustment using setting
    std_dev_excess = excess_ret.std()
    if std_dev_excess == 0 or excess_ret.empty:
        sharpe = 0.0  # Or handle as appropriate
    else:
        # Use annualization factor setting
        sharpe = float(
            np.sqrt(annualization_factor) * excess_ret.mean() / std_dev_excess
        )

    # Correlation analysis (Core Logic)
    correlation = (
        float(sym_ret.corr(mkt_ret))
        if not sym_ret.empty and not mkt_ret.empty
        else np.nan
    )

    # Risk scoring based on multiple metrics (Core Logic)
    # Handle potential NaN values from calculations
    beta_score = max(0, 1 - abs(beta - 1)) if not np.isnan(beta) else 0
    var_score = (
        max(0, 1 + var / 0.05) if not np.isnan(var) else 0
    )  # Normalize VaR (0.05 could also be a setting)
    sharpe_score = (
        min(1, max(0, sharpe / 3)) if not np.isnan(sharpe) else 0
    )  # Normalization (3 could also be a setting)

    # Use weights from settings
    composite_score = (
        beta_score * beta_settings.COMPOSITE_WEIGHT_BETA
        + var_score * beta_settings.COMPOSITE_WEIGHT_VAR
        + sharpe_score * beta_settings.COMPOSITE_WEIGHT_SHARPE
    )

    # Use thresholds from settings
    # Corrected if/elif/else block
    if composite_score > beta_settings.VERDICT_THRESHOLD_LOW_RISK:
        verdict = "LOW_RISK"
    elif composite_score > beta_settings.VERDICT_THRESHOLD_MODERATE_RISK:
        verdict = "MODERATE_RISK"
    else:
        verdict = "HIGH_RISK"

    # Create success result dictionary (Core Logic)
    # Use confidence level in VaR key
    var_key = f"value_at_risk_{int(confidence_level * 100)}"
    # Corrected dictionary structure
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(
            composite_score * 100, 2
        ),  # Use composite score for confidence
        "value": (
            round(beta, 4) if not np.isnan(beta) else None
        ),  # Beta as primary value
        "details": {
            "beta": round(beta, 4) if not np.isnan(beta) else None,
            var_key: (
                round(var * 100, 2) if not np.isnan(var) else None
            ),  # Use dynamic key
            "sharpe_ratio": round(sharpe, 2) if not np.isnan(sharpe) else None,
            "market_correlation": (
                round(correlation, 2) if not np.isnan(correlation) else None
            ),
            "market_index_used": market_symbol,
            "risk_scores": {
                "beta_component": round(beta_score, 2),
                "var_component": round(var_score, 2),
                "sharpe_component": round(sharpe_score, 2),
            },
            "config_used": {  # Add config details for traceability
                "var_confidence_level": confidence_level,
                "sharpe_annualization_factor": annualization_factor,
                "risk_free_rate": risk_free,
                "weights": {
                    "beta": beta_settings.COMPOSITE_WEIGHT_BETA,
                    "var": beta_settings.COMPOSITE_WEIGHT_VAR,
                    "sharpe": beta_settings.COMPOSITE_WEIGHT_SHARPE,
                },
                "thresholds": {
                    "low_risk": beta_settings.VERDICT_THRESHOLD_LOW_RISK,
                    "moderate_risk": beta_settings.VERDICT_THRESHOLD_MODERATE_RISK,
                },
            },
        },
        "score": round(composite_score, 4),  # Keep composite score if needed elsewhere
        "agent_name": agent_name,  # Decorator might overwrite this
    }

    # Decorator handles caching and tracker update
    return result
