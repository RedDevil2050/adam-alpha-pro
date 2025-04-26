import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from scipy.stats import norm
from sklearn.cluster import KMeans

class MarketAnalysis:
    def __init__(self, data_service):
        self.data_service = data_service
        self.regime_states = {}

    async def analyze_market_regime(self, symbols: List[str]) -> Dict[str, str]:
        """Analyze market regime using multiple factors"""
        try:
            data = await self.data_service.get_market_data(symbols)
            returns = data.pct_change().dropna()
            
            # Calculate regime indicators
            volatility = returns.std() * np.sqrt(252)
            correlation = returns.corr().mean().mean()
            trend = self._calculate_trend_strength(data)
            
            # Classify regime
            regime = self._classify_regime(volatility, correlation, trend)
            return {'regime': regime, 'confidence': self._regime_confidence()}
        except Exception as e:
            return {'regime': 'unknown', 'confidence': 0.0}

    def _classify_regime(self, volatility: float, correlation: float, trend: float) -> str:
        """Classify market regime using clustering"""
        features = np.array([[volatility, correlation, trend]])
        kmeans = KMeans(n_clusters=4, random_state=42)
        regime = kmeans.fit_predict(features)[0]
        
        regime_map = {
            0: 'risk_on',
            1: 'risk_off',
            2: 'transition',
            3: 'crisis'
        }
        return regime_map.get(regime, 'unknown')
