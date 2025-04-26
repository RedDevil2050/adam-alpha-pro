import numpy as np
import pandas as pd
from typing import Dict, List

class TechnicalIndicators:
    @staticmethod
    def calculate_all(data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate comprehensive technical indicators"""
        results = {}
        
        # Momentum indicators
        results['rsi'] = TechnicalIndicators.rsi(data['close'])
        results['macd'] = TechnicalIndicators.macd(data['close'])
        results['adx'] = TechnicalIndicators.adx(data)
        
        # Volume indicators
        results['obv'] = TechnicalIndicators.on_balance_volume(data)
        results['vwap'] = TechnicalIndicators.vwap(data)
        
        # Volatility indicators
        results['bbands'] = TechnicalIndicators.bollinger_bands(data['close'])
        results['atr'] = TechnicalIndicators.average_true_range(data)
        
        # Mean reversion
        results['hurst'] = TechnicalIndicators.hurst_exponent(data['close'])
        results['half_life'] = TechnicalIndicators.half_life(data['close'])
        
        return results

    @staticmethod
    def hurst_exponent(series: pd.Series, lags: range = range(2, 100)) -> float:
        """Calculate Hurst exponent for mean reversion analysis"""
        tau = [np.std(np.subtract(series[lag:], series[:-lag])) for lag in lags]
        reg = np.polyfit(np.log(lags), np.log(tau), 1)
        return reg[0]

    @staticmethod
    def half_life(series: pd.Series) -> float:
        """Calculate mean reversion half-life"""
        lag = series.shift(1)
        delta = series - lag
        lag2 = sm.add_constant(lag)
        model = sm.OLS(delta[1:], lag2[1:])
        res = model.fit()
        return -np.log(2) / res.params[1]
