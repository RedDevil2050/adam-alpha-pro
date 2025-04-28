import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, List, Tuple


class QuantCore:
    @staticmethod
    def calculate_factors(returns: pd.DataFrame) -> pd.DataFrame:
        """Fama-French 3-factor model implementation"""
        mkt = returns["SPY"].mean()  # Market factor
        size = returns[returns.columns].std()  # Size factor
        value = returns.skew()  # Value factor
        return pd.DataFrame({"market": mkt, "size": size, "value": value})

    @staticmethod
    def calculate_risk_metrics(returns: pd.Series) -> Dict[str, float]:
        """Advanced risk metrics calculation"""
        annualized_ret = returns.mean() * 252
        vol = returns.std() * np.sqrt(252)
        sharpe = annualized_ret / vol if vol != 0 else 0

        # Calculate VaR using both historical and parametric methods
        hist_var_95 = np.percentile(returns, 5)
        param_var_95 = norm.ppf(0.05, returns.mean(), returns.std())

        return {
            "sharpe": sharpe,
            "sortino": QuantCore.calculate_sortino(returns),
            "hist_var_95": hist_var_95,
            "param_var_95": param_var_95,
            "max_drawdown": QuantCore.calculate_max_drawdown(returns),
        }

    @staticmethod
    def calculate_sortino(returns: pd.Series, risk_free: float = 0.02) -> float:
        downside = returns[returns < risk_free]
        if len(downside) == 0:
            return np.inf
        downside_std = downside.std() * np.sqrt(252)
        excess_ret = (returns.mean() - risk_free / 252) * 252
        return excess_ret / downside_std if downside_std != 0 else 0

    @staticmethod
    def calculate_max_drawdown(returns: pd.Series) -> float:
        cum_rets = (1 + returns).cumprod()
        rolling_max = cum_rets.expanding().max()
        drawdowns = cum_rets / rolling_max - 1
        return drawdowns.min()

    @staticmethod
    def analyze_market_state(
        returns: pd.DataFrame, vix_data: pd.Series
    ) -> Dict[str, float]:
        """Analyze current market state using multiple indicators"""
        market_metrics = {
            "trend": QuantCore._calculate_trend_strength(returns["SPY"]),
            "volatility": QuantCore._calculate_volatility_regime(vix_data),
            "momentum": QuantCore._calculate_momentum_score(returns["SPY"]),
            "market_quality": QuantCore._calculate_market_quality(returns),
        }
        return market_metrics

    @staticmethod
    def _calculate_trend_strength(price_data: pd.Series, window: int = 20) -> float:
        """Calculate trend strength using moving averages"""
        ma_short = price_data.rolling(window=window).mean()
        ma_long = price_data.rolling(window=window * 2).mean()
        trend_strength = (ma_short - ma_long) / ma_long
        return float(trend_strength.iloc[-1])

    @staticmethod
    def _calculate_volatility_regime(vix: pd.Series, lookback: int = 20) -> float:
        """Determine volatility regime using VIX"""
        current_vix = vix.iloc[-1]
        historical_mean = vix.rolling(window=lookback).mean().iloc[-1]
        vol_score = (current_vix - historical_mean) / vix.rolling(
            window=lookback
        ).std().iloc[-1]
        return float(vol_score)

    @staticmethod
    def _calculate_momentum_score(
        returns: pd.Series, windows: List[int] = [5, 10, 20]
    ) -> float:
        """Calculate multi-timeframe momentum score"""
        momentum_scores = []
        for window in windows:
            ret = returns.rolling(window=window).mean().iloc[-1]
            momentum_scores.append(np.sign(ret))
        return float(np.mean(momentum_scores))

    @staticmethod
    def _calculate_market_quality(returns: pd.DataFrame) -> float:
        """Calculate market quality score based on correlation and dispersion"""
        correlations = returns.corr()
        avg_correlation = (correlations.sum().sum() - len(correlations)) / (
            len(correlations) ** 2 - len(correlations)
        )
        dispersion = returns.std().mean()
        return float(0.5 * (1 - avg_correlation) + 0.5 * (1 - dispersion))

    @staticmethod
    def get_market_readiness(market_state: Dict[str, float]) -> Tuple[bool, float]:
        """Determine if market is ready for trading based on state metrics"""
        weights = {
            "trend": 0.3,
            "volatility": 0.2,
            "momentum": 0.3,
            "market_quality": 0.2,
        }

        readiness_score = sum(market_state[k] * weights[k] for k in weights)
        is_ready = readiness_score > 0.6  # Threshold for market readiness

        return is_ready, readiness_score
