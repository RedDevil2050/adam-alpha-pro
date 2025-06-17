import pandas as pd
import numpy as np
from backend.utils.progress_tracker import ProgressTracker

# Instantiate a shared tracker
tracker = ProgressTracker(filepath="backend/utils/progress.json")


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period, min_periods=period).mean().iloc[-1]
    rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Computes the Average True Range (ATR)."""
    if not (isinstance(high, pd.Series) and isinstance(low, pd.Series) and isinstance(close, pd.Series)):
        raise ValueError("Inputs high, low, close must be pandas Series.")
    if not (len(high) == len(low) == len(close)):
        raise ValueError("Input series must have the same length.")
    if len(high) < period:
        return np.nan # Not enough data to compute ATR

    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    
    true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    
    # Wilder's smoothing for ATR
    atr = true_range.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    
    if atr.empty or pd.isna(atr.iloc[-1]):
        return np.nan
    return float(atr.iloc[-1])


def normalize_rsi(rsi: float) -> float:
    if rsi <= 30:
        return 1.0
    if rsi >= 70:
        return 0.0
    return float((70 - rsi) / 40)
