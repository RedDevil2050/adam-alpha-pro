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
    rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)

def normalize_rsi(rsi: float) -> float:
    if rsi <= 30:
        return 1.0
    if rsi >= 70:
        return 0.0
    return float((70 - rsi) / 40)
