import numpy as np
from sklearn.mixture import GaussianMixture
from typing import Dict, Tuple

class MarketRegimeDetector:
    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes
        self.gmm = GaussianMixture(n_components=n_regimes, random_state=42)
        
    def detect_regime(self, returns: np.array, volatility: np.array) -> Dict[str, float]:
        """Detect market regime using returns and volatility"""
        features = np.column_stack([returns, volatility])
        regime = self.gmm.fit_predict(features)
        
        # Get latest regime
        current_regime = regime[-1]
        regime_probs = self.gmm.predict_proba(features)[-1]
        
        return {
            'current_regime': int(current_regime),
            'regime_probability': float(regime_probs[current_regime]),
            'regime_volatility': float(self.gmm.covariances_[current_regime][1,1])
        }
