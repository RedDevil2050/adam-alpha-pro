import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from sklearn.cluster import KMeans
from scipy import stats
from sklearn.linear_model import LinearRegression

@dataclass
class MarketState:
    regime: str
    volatility: float
    correlation: float
    liquidity: float
    sentiment: float

class MarketAnalyzer:
    def __init__(self, data_service):
        self.data_service = data_service
        self.market_states = {}
        self.regime_model = self._initialize_regime_model()

    async def analyze_market_state(self, symbols: List[str]) -> MarketState:
        try:
            data = await self.data_service.get_market_data(symbols)
            volatility = self._calculate_market_volatility(data)
            correlation = self._calculate_cross_correlation(data)
            liquidity = await self._analyze_market_liquidity(symbols)
            sentiment = await self._analyze_market_sentiment(symbols)
            
            regime = self._classify_market_regime(volatility, correlation, liquidity)
            return MarketState(regime, volatility, correlation, liquidity, sentiment)
        except Exception as e:
            logging.error(f"Market analysis failed: {e}")
            return None

    def _initialize_regime_model(self) -> KMeans:
        return KMeans(n_clusters=4, random_state=42)

    def _classify_market_regime(self, volatility: float, correlation: float, 
                              liquidity: float) -> str:
        features = np.array([[volatility, correlation, liquidity]])
        regime = self.regime_model.predict(features)[0]
        regimes = ['normal', 'stress', 'crisis', 'recovery']
        return regimes[regime]

    def _calculate_market_volatility(self, data: pd.DataFrame) -> float:
        returns = data.pct_change().dropna()
        return float(returns.std() * np.sqrt(252))

    def _calculate_cross_correlation(self, data: pd.DataFrame) -> float:
        returns = data.pct_change().dropna()
        corr_matrix = returns.corr()
        return float(corr_matrix.mean().mean())

    async def _analyze_market_liquidity(self, symbols: List[str]) -> float:
        liquidity_scores = []
        for symbol in symbols:
            market_health = await self.data_service.get_market_health(symbol)
            liquidity_scores.append(market_health['liquidity'].get('liquidity_score', 0))
        return float(np.mean(liquidity_scores))

    async def _analyze_market_sentiment(self, symbols: List[str]) -> float:
        sentiment_scores = []
        for symbol in symbols:
            analytics = await self.data_service.get_advanced_analytics(symbol)
            momentum = analytics.get('momentum', {})
            sentiment_scores.append(self._calculate_sentiment_score(momentum))
        return float(np.mean(sentiment_scores))

    def _calculate_sentiment_score(self, momentum_data: Dict) -> float:
        weights = {'roc': 0.4, 'cci': 0.3, 'ultimate_osc': 0.3}
        score = sum(momentum_data.get(k, 0) * v for k, v in weights.items())
        return min(max(score, -1), 1)  # Normalize between -1 and 1

    async def get_market_statistics(self, symbols: List[str], lookback: int = 252) -> Dict[str, float]:
        try:
            data = await self.data_service.get_market_data(symbols, lookback)
            returns = data.pct_change().dropna()
            
            stats = {
                'beta': self._calculate_market_beta(returns),
                'alpha': self._calculate_jensen_alpha(returns),
                'information_ratio': self._calculate_information_ratio(returns),
                'tracking_error': self._calculate_tracking_error(returns)
            }
            return stats
        except Exception as e:
            logging.error(f"Market statistics calculation failed: {e}")
            return {}

    def _calculate_market_beta(self, returns: pd.DataFrame) -> float:
        market_returns = returns['SPY']  # Assuming SPY as market proxy
        stock_returns = returns.drop('SPY', axis=1)
        
        betas = {}
        for column in stock_returns.columns:
            slope, _, _, _, _ = stats.linregress(market_returns, stock_returns[column])
            betas[column] = slope
        return float(np.mean(list(betas.values())))

    def _analyze_regime_transition(self) -> Dict[str, float]:
        current_state = self.market_states.get('current')
        if not current_state:
            return {}
            
        transition_probs = {
            'stress_prob': self._calculate_stress_probability(),
            'recovery_prob': self._calculate_recovery_probability(),
            'regime_persistence': self._calculate_regime_persistence()
        }
        return transition_probs
