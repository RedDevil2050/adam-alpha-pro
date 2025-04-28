import numpy as np
from sklearn.mixture import GaussianMixture
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.agents.ml.utils import tracker

agent_name = "market_regime_agent"


class MarketRegimeDetector:
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.gmm = GaussianMixture(n_components=n_regimes, random_state=42)

    def detect_regime(self, returns: np.array, volatility: np.array) -> dict:
        """Detect market regime using returns and volatility"""
        features = np.column_stack([returns, volatility])
        regime = self.gmm.fit_predict(features)

        # Get latest regime
        current_regime = regime[-1]
        regime_probs = self.gmm.predict_proba(features)[-1]

        return {
            "current_regime": int(current_regime),
            "regime_probability": float(regime_probs[current_regime]),
            "regime_volatility": float(self.gmm.covariances_[current_regime][1, 1]),
        }


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        # Fetch price series
        prices = await fetch_price_series(symbol)
        if not prices or len(prices) < 60:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "agent_name": agent_name,
            }

        # Calculate returns and volatility
        returns = np.diff(np.log(prices))
        volatility = np.std(returns[-30:])

        # Detect market regime
        detector = MarketRegimeDetector()
        regime_data = detector.detect_regime(returns, np.full_like(returns, volatility))

        result = {
            "symbol": symbol,
            "verdict": f"REGIME_{regime_data['current_regime']}",
            "confidence": round(regime_data["regime_probability"], 4),
            "value": regime_data["current_regime"],
            "details": regime_data,
            "agent_name": agent_name,
        }

        await redis_client.set(cache_key, result, ex=3600)
        tracker.update("ml", agent_name, "implemented")
        return result

    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name,
        }
