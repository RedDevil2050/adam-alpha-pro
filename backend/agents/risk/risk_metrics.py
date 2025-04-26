import numpy as np
import pandas as pd
from scipy import stats

def calculate_var(returns, confidence=0.95):
    """Value at Risk calculation"""
    return np.percentile(returns, (1-confidence)*100)

def calculate_cvar(returns, confidence=0.95):
    """Conditional Value at Risk"""
    var = calculate_var(returns, confidence)
    return returns[returns <= var].mean()

def calculate_sortino_ratio(returns, risk_free=0.04):
    """Sortino Ratio - only penalizes downside volatility"""
    excess_returns = returns - risk_free/252
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.std(returns)
    return np.sqrt(252) * excess_returns.mean() / downside_std

def calculate_information_ratio(returns, benchmark_returns):
    """Information Ratio - risk-adjusted excess returns vs benchmark"""
    active_returns = returns - benchmark_returns
    return np.sqrt(252) * active_returns.mean() / active_returns.std()
