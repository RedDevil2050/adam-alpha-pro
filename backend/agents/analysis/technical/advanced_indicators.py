import numpy as np
import pandas as pd


def calculate_hurst_exponent(series, max_lag=20):
    """Calculate Hurst exponent - measure of long-term memory"""
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
    return np.polyfit(np.log(lags), np.log(tau), 1)[0]


def calculate_vwap(df):
    """Volume Weighted Average Price"""
    return (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()


def calculate_fibonacci_levels(high, low):
    """Fibonacci retracement levels"""
    diff = high - low
    levels = {
        "23.6%": high - 0.236 * diff,
        "38.2%": high - 0.382 * diff,
        "50.0%": high - 0.500 * diff,
        "61.8%": high - 0.618 * diff,
    }
    return levels


def calculate_momentum_quality(series, period=14):
    """Momentum Quality based on directional changes"""
    changes = np.diff(series)
    positive_moves = np.sum(changes > 0) / len(changes)
    return positive_moves * 100
