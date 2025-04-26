import numpy as np
import pandas as pd
from typing import Dict, List

def calculate_ichimoku(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Ichimoku Cloud technical indicator"""
    high = df['high']
    low = df['low']
    
    tenkan_window = 9
    kijun_window = 26
    senkou_span_b_window = 52
    
    tenkan_sen = (high.rolling(tenkan_window).max() + low.rolling(tenkan_window).min()) / 2
    kijun_sen = (high.rolling(kijun_window).max() + low.rolling(kijun_window).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_window)
    senkou_span_b = ((high.rolling(senkou_span_b_window).max() + low.rolling(senkou_span_b_window).min()) / 2).shift(kijun_window)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b
    }

def calculate_volume_profile(df: pd.DataFrame, bins: int = 10) -> Dict[float, float]:
    """Volume Profile analysis"""
    price_bins = pd.cut(df['close'], bins=bins)
    volume_profile = df.groupby(price_bins)['volume'].sum()
    return dict(zip(volume_profile.index.astype(str), volume_profile.values))

def calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate pivot points and support/resistance levels"""
    high = df['high'].iloc[-1]
    low = df['low'].iloc[-1]
    close = df['close'].iloc[-1]
    
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    
    return {
        'pivot': pivot,
        'r1': r1,
        'r2': r2,
        's1': s1,
        's2': s2
    }
