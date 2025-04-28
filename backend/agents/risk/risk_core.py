import numpy as np
import pandas as pd
from scipy import stats


def calculate_risk_metrics(
    returns: pd.Series, benchmark_returns: pd.Series = None
) -> Dict[str, float]:
    """Comprehensive risk analysis"""
    var_95 = np.percentile(returns, 5)
    es_95 = returns[returns <= var_95].mean()

    # Downside deviation
    downside_returns = returns[returns < 0]
    downside_deviation = np.sqrt(np.mean(downside_returns**2))

    # Maximum drawdown
    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdowns = cum_returns / rolling_max - 1
    max_drawdown = drawdowns.min()

    # Tail risk metrics
    kurtosis = stats.kurtosis(returns)
    skewness = stats.skew(returns)

    return {
        "var_95": var_95,
        "expected_shortfall": es_95,
        "downside_deviation": downside_deviation,
        "max_drawdown": max_drawdown,
        "tail_metrics": {"kurtosis": kurtosis, "skewness": skewness},
    }
