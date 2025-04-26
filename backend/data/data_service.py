import yfinance as yf
import pandas_datareader as pdr
import pandas as pd
import redis
import logging
from typing import List, Dict, Optional, Union, Any
import asyncio
import aiohttp
import websockets
from datetime import datetime, timedelta
from functools import lru_cache
from scipy.stats import norm, pearsonr
from sklearn.preprocessing import StandardScaler
from arch import arch_model

class DataService:
    def __init__(self):
        self.primary_source = "yahoo"
        self.backup_source = "alpha_vantage"
        self.api_keys = self._load_api_keys()
        self.cache = redis.Redis(host='localhost', port=6379, db=0)
        self.websocket_url = "wss://ws.finnhub.io"
        self.logger = self._setup_logger()
        self.rate_limiter = asyncio.Semaphore(5)  # Rate limiting

    async def get_market_data(self, symbols: List[str], lookback_period: int = 252) -> pd.DataFrame:
        """Enhanced dual-channel data acquisition with caching"""
        cache_key = f"market_data_{'-'.join(symbols)}_{lookback_period}"
        cached_data = self._get_from_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
            
        async with self.rate_limiter:
            try:
                data = await self._fetch_primary_data(symbols, lookback_period)
                self._cache_data(cache_key, data)
                return data
            except Exception as e:
                self.logger.error(f"Primary source failed: {e}")
                return await self._fetch_backup_data(symbols, lookback_period)

    async def stream_real_time_data(self, symbols: List[str]):
        """Real-time market data streaming"""
        async with websockets.connect(f"{self.websocket_url}?token={self.api_keys['finnhub']}") as websocket:
            for symbol in symbols:
                await websocket.send(f'{{"type":"subscribe","symbol":"{symbol}"}}')
            
            while True:
                try:
                    data = await websocket.recv()
                    yield self._process_websocket_data(data)
                except Exception as e:
                    self.logger.error(f"Websocket error: {e}")
                    await asyncio.sleep(1)

    @lru_cache(maxsize=100)
    async def get_fundamental_data(self, symbol: str) -> Dict[str, Union[float, str]]:
        """Fetch fundamental data with caching"""
        async with self.rate_limiter:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                return {
                    'market_cap': info.get('marketCap'),
                    'pe_ratio': info.get('trailingPE'),
                    'dividend_yield': info.get('dividendYield'),
                    'beta': info.get('beta')
                }
            except Exception as e:
                self.logger.error(f"Failed to fetch fundamental data: {e}")
                return {}

    async def get_market_indicators(self, symbol: str) -> Dict[str, float]:
        """Get technical and market indicators"""
        cache_key = f"indicators_{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        async with self.rate_limiter:
            try:
                data = await self._fetch_primary_data([symbol], 100)
                indicators = {
                    'rsi': self._calculate_rsi(data[symbol]),
                    'macd': self._calculate_macd(data[symbol]),
                    'bollinger': self._calculate_bollinger_bands(data[symbol])
                }
                self._cache_data(cache_key, indicators, expiry=1800)
                return indicators
            except Exception as e:
                self.logger.error(f"Indicator calculation failed: {e}")
                return {}

    async def get_advanced_analytics(self, symbol: str) -> Dict[str, Any]:
        """Get advanced market analytics"""
        cache_key = f"advanced_{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        async with self.rate_limiter:
            try:
                data = await self._fetch_primary_data([symbol], 252)
                analytics = {
                    'technical': await self._get_technical_indicators(data[symbol]),
                    'statistical': self._get_statistical_metrics(data[symbol]),
                    'volatility': self._get_volatility_metrics(data[symbol]),
                    'momentum': self._get_momentum_indicators(data[symbol])
                }
                self._cache_data(cache_key, analytics, expiry=1800)
                return analytics
            except Exception as e:
                self.logger.error(f"Advanced analytics failed: {e}")
                return {}

    async def get_market_health(self, symbol: str) -> Dict[str, Any]:
        """Market health analysis"""
        try:
            data = await self._fetch_primary_data([symbol], 252)
            return {
                'liquidity': self._analyze_liquidity(data[symbol]),
                'market_impact': self._estimate_market_impact(data[symbol]),
                'microstructure': await self._analyze_microstructure(symbol),
                'regime': self._detect_market_regime(data[symbol])
            }
        except Exception as e:
            self.logger.error(f"Market health analysis failed: {e}")
            return {}

    def _analyze_microstructure(self, symbol: str) -> Dict[str, float]:
        return {
            'spread': self._calculate_spread(symbol),
            'depth': self._calculate_market_depth(symbol),
            'resilience': self._calculate_market_resilience(symbol)
        }

    def _detect_market_regime(self, prices: pd.Series) -> str:
        volatility = self._calculate_realized_volatility(prices)
        trend = self._calculate_trend_strength(prices)
        return self._classify_regime(volatility, trend)

    def _get_statistical_metrics(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate advanced statistical metrics"""
        returns = prices.pct_change().dropna()
        return {
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
            'var_95': norm.ppf(0.05, returns.mean(), returns.std()),
            'cvar_95': returns[returns <= norm.ppf(0.05, returns.mean(), returns.std())].mean()
        }

    def _get_volatility_metrics(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate volatility metrics"""
        returns = prices.pct_change().dropna()
        return {
            'historical_vol': returns.std() * np.sqrt(252),
            'parkinson_vol': self._parkinson_volatility(prices),
            'garch_vol': self._garch_volatility(returns)
        }

    def _get_momentum_indicators(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate momentum indicators"""
        return {
            'roc': self._rate_of_change(prices),
            'cci': self._commodity_channel_index(prices),
            'ultimate_osc': self._ultimate_oscillator(prices)
        }

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

    def _calculate_macd(self, prices: pd.Series) -> Dict[str, float]:
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        return {'macd': macd.iloc[-1], 'signal': signal.iloc[-1]}

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20) -> Dict[str, float]:
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        return {
            'upper': (sma + (std * 2)).iloc[-1],
            'lower': (sma - (std * 2)).iloc[-1],
            'middle': sma.iloc[-1]
        }

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger('DataService')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler('data_service.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def _get_from_cache(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve data from cache"""
        try:
            cached = self.cache.get(key)
            if cached:
                return pd.read_json(cached)
        except Exception as e:
            self.logger.error(f"Cache retrieval error: {e}")
        return None

    def _cache_data(self, key: str, data: pd.DataFrame, expiry: int = 3600):
        """Cache market data"""
        try:
            self.cache.setex(key, expiry, data.to_json())
        except Exception as e:
            self.logger.error(f"Cache storage error: {e}")

    def _process_websocket_data(self, data: str) -> Dict:
        """Process incoming websocket data"""
        try:
            parsed = json.loads(data)
            return {
                'symbol': parsed['data'][0]['s'],
                'price': parsed['data'][0]['p'],
                'timestamp': parsed['data'][0]['t'],
                'volume': parsed['data'][0]['v']
            }
        except Exception as e:
            self.logger.error(f"Websocket data processing error: {e}")
            return {}

    async def _fetch_primary_data(self, symbols: List[str], lookback_period: int) -> pd.DataFrame:
        data = {}
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{lookback_period}d")
            data[symbol] = hist['Close']
        return pd.DataFrame(data)

    async def _fetch_backup_data(self, symbols: List[str], lookback_period: int) -> pd.DataFrame:
        start = datetime.now() - timedelta(days=lookback_period)
        data = {}
        for symbol in symbols:
            df = pdr.get_data_alpha_vantage(
                symbol,
                start=start,
                api_key=self.api_keys['alpha_vantage']
            )
            data[symbol] = df['close']
        return pd.DataFrame(data)

    def _load_api_keys(self) -> Dict[str, str]:
        # Implement secure API key loading
        return {
            "alpha_vantage": "YOUR_API_KEY",
            "finnhub": "YOUR_API_KEY"
        }
