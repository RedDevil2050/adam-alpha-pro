import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from scipy.optimize import minimize


class QuantStrategies:
    @staticmethod
    def adaptive_momentum(
        returns: pd.DataFrame, lookback: List[int] = [20, 60, 120]
    ) -> Dict[str, float]:
        signals = {}
        for period in lookback:
            momentum = returns.rolling(period).mean()
            vol = returns.rolling(period).std()
            signals[f"momentum_{period}"] = momentum.iloc[-1] / vol.iloc[-1]
        return signals

    @staticmethod
    def risk_parity_allocation(
        returns: pd.DataFrame, risk_target: float = 0.15
    ) -> Dict[str, float]:
        cov_matrix = returns.cov() * 252
        n_assets = len(returns.columns)

        def objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            risk_contrib = weights * (np.dot(cov_matrix, weights)) / portfolio_vol
            return np.sum((risk_contrib - portfolio_vol / n_assets) ** 2)

        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},
            {"type": "ineq", "fun": lambda x: x},
        ]

        result = minimize(
            objective,
            x0=np.ones(n_assets) / n_assets,
            method="SLSQP",
            constraints=constraints,
        )

        return dict(zip(returns.columns, result.x))

    @staticmethod
    def regime_detection(returns: pd.DataFrame, vix_data: pd.Series) -> str:
        vol = returns.std() * np.sqrt(252)
        current_vix = vix_data.iloc[-1]
        vix_percentile = pd.Series(vix_data).rank(pct=True).iloc[-1]

        if vix_percentile > 0.8:
            return "high_volatility"
        elif vix_percentile < 0.2:
            return "low_volatility"
        return "normal"
