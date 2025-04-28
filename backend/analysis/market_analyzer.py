import asyncio
import logging
from typing import Dict, List, Optional
from backend.utils.metrics_collector import monitor_execution_time
from backend.utils.validation import validate_input
from backend.utils.cache_utils import cache_data, cleanup_cache
from backend.monitoring.performance import track_memory_usage
import numpy as np
import pandas as pd
from dataclasses import dataclass
from sklearn.cluster import KMeans
from scipy import stats
from sklearn.linear_model import LinearRegression
from functools import cached_property


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
        self._volatility_window = 252  # Configure as class constant
        self._sentiment_weights = {"roc": 0.4, "cci": 0.3, "ultimate_osc": 0.3}
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = 0

    async def _maybe_cleanup_cache(self):
        """Periodically cleanup old cache entries"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            await cleanup_cache()
            self._last_cleanup = now

    @monitor_execution_time("market_analysis")
    @track_memory_usage()
    @validate_input(min_symbols=1, max_symbols=100)
    async def analyze_market_state(self, symbols: List[str]) -> Optional[MarketState]:
        await self._maybe_cleanup_cache()
        try:
            # Parallel fetch of all required data
            data_task = self.data_service.get_market_data(symbols)
            liquidity_task = self._analyze_market_liquidity(symbols)
            sentiment_task = self._analyze_market_sentiment(symbols)

            data, liquidity, sentiment = await asyncio.gather(
                data_task, liquidity_task, sentiment_task
            )

            # Vectorized calculations
            volatility = self._calculate_market_volatility(data)
            correlation = self._calculate_cross_correlation(data)
            regime = self._classify_market_regime(volatility, correlation, liquidity)

            return MarketState(regime, volatility, correlation, liquidity, sentiment)
        except Exception as e:
            logging.error(f"Market analysis failed: {e}", exc_info=True)
            return None

    def _initialize_regime_model(self) -> KMeans:
        return KMeans(n_clusters=4, random_state=42)

    @monitor_execution_time("regime_classification")
    def _classify_market_regime(
        self, volatility: float, correlation: float, liquidity: float
    ) -> str:
        features = np.array([[volatility, correlation, liquidity]])
        regime = self.regime_model.predict(features)[0]
        regimes = ["normal", "stress", "crisis", "recovery"]
        return regimes[regime]

    def _calculate_market_volatility(self, data: pd.DataFrame) -> float:
        returns = data.pct_change().dropna()
        return float(returns.std() * np.sqrt(252))

    def _calculate_cross_correlation(self, data: pd.DataFrame) -> float:
        returns = data.pct_change().dropna()
        corr_matrix = returns.corr()
        return float(corr_matrix.mean().mean())

    @cache_data(ttl=300)  # Cache for 5 minutes
    async def _analyze_market_liquidity(self, symbols: List[str]) -> float:
        tasks = [self.data_service.get_market_health(symbol) for symbol in symbols]
        market_health_results = await asyncio.gather(*tasks)
        liquidity_scores = [
            health["liquidity"].get("liquidity_score", 0)
            for health in market_health_results
        ]
        return float(np.mean(liquidity_scores))

    @cache_data(ttl=300)
    async def _analyze_market_sentiment(self, symbols: List[str]) -> float:
        tasks = [self.data_service.get_advanced_analytics(symbol) for symbol in symbols]
        analytics_results = await asyncio.gather(*tasks)
        sentiment_scores = [
            self._calculate_sentiment_score(analytics.get("momentum", {}))
            for analytics in analytics_results
        ]
        return float(np.mean(sentiment_scores))

    @lru_cache(maxsize=128)
    def _calculate_sentiment_score(self, momentum_data: Dict) -> float:
        score = sum(
            momentum_data.get(k, 0) * v for k, v in self._sentiment_weights.items()
        )
        return min(max(score, -1), 1)  # Normalize between -1 and 1

    @monitor_execution_time("market_statistics")
    @track_memory_usage()
    @validate_input(min_symbols=1, max_symbols=500)
    async def get_market_statistics(
        self, symbols: List[str], lookback: int = 252
    ) -> Dict[str, float]:
        await self._maybe_cleanup_cache()
        try:
            chunk_size = min(
                50, len(symbols)
            )  # Ensure chunk_size doesn't exceed symbols length
            chunks = [
                symbols[i : i + chunk_size] for i in range(0, len(symbols), chunk_size)
            ]

            # Process chunks concurrently
            chunk_tasks = [
                self._process_statistics_chunk(chunk, lookback) for chunk in chunks
            ]
            all_stats = await asyncio.gather(*chunk_tasks)

            # Combine results
            if not all_stats:
                return {}

            return {
                k: np.mean([s[k] for s in all_stats if k in s])
                for k in all_stats[0].keys()
            }
        except Exception as e:
            logging.error(f"Market statistics calculation failed: {e}", exc_info=True)
            return {}

    async def _process_statistics_chunk(
        self, symbols: List[str], lookback: int
    ) -> Dict[str, float]:
        """Process a single chunk of symbols for statistics calculation"""
        data = await self.data_service.get_market_data(symbols, lookback)
        returns = data.pct_change().dropna()

        return {
            "beta": self._calculate_market_beta(returns),
            "alpha": self._calculate_jensen_alpha(returns),
            "information_ratio": self._calculate_information_ratio(returns),
            "tracking_error": self._calculate_tracking_error(returns),
        }

    @monitor_execution_time("market_beta")
    def _calculate_market_beta(self, returns: pd.DataFrame) -> float:
        try:
            market_returns = returns["SPY"]
            stock_returns = returns.drop("SPY", axis=1)

            # Vectorized beta calculation
            cov = stock_returns.cov()["SPY"]
            market_var = market_returns.var()
            betas = cov / market_var

            return float(betas.mean())
        except KeyError:
            logging.warning("SPY data not found, using fallback beta calculation")
            return self._calculate_fallback_beta(returns)

    @staticmethod
    def _calculate_fallback_beta(returns: pd.DataFrame) -> float:
        # Implement fallback calculation
        return 1.0

    def _analyze_regime_transition(self) -> Dict[str, float]:
        current_state = self.market_states.get("current")
        if not current_state:
            return {}

        transition_probs = {
            "stress_prob": self._calculate_stress_probability(),
            "recovery_prob": self._calculate_recovery_probability(),
            "regime_persistence": self._calculate_regime_persistence(),
        }
        return transition_probs
