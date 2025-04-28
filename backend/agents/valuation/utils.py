# File: backend/agents/valuation/utils.py
import statistics
from typing import Optional, Sequence
from backend.config.settings import settings

def screen_quantitative(
    value: Optional[float],
    peers: Sequence[float]
) -> dict:
    """
    Screen a metric against a peer distribution using quant z-score or percentile methods.
    Returns dict with keys: verdict, confidence, mean (if z-score), z_score (if z-score).
    """
    result = {'verdict': 'NO_DATA', 'confidence': 0.0, 'mean': None, 'z_score': None}
    if value is None or not peers:
        return result

    mode = settings.VALUATION_MODE.lower()
    if mode == 'percentile':
        arr = sorted(peers + [value])
        rank = arr.index(value) / len(arr)
        low, high = settings.PCT_LOWER, settings.PCT_UPPER
        if rank <= low:
            verdict = 'UNDERVALUE'
        elif rank >= high:
            verdict = 'OVERVALUE'
        else:
            verdict = 'FAIR_VALUE'
        confidence = abs(rank - 0.5) * 2 * 100
        result.update(verdict=verdict, confidence=round(confidence, 2))
    else:
        mu = statistics.mean(peers)
        sigma = statistics.stdev(peers) if len(peers) > 1 else 0.0
        z = ((value - mu) / sigma) if sigma else 0.0
        # z-score bands
        if z <= settings.Z_LOWER_STRONG:
            verdict = 'STRONG_UNDERVALUE'
        elif z <= settings.Z_LOWER_MILD:
            verdict = 'UNDERVALUE'
        elif z < settings.Z_UPPER_MILD:
            verdict = 'FAIR_VALUE'
        elif z < settings.Z_UPPER_STRONG:
            verdict = 'OVERVALUE'
        else:
            verdict = 'STRONG_OVERVALUE'
        confidence = min(abs(z) * 50, 100)
        result.update(verdict=verdict, confidence=round(confidence, 2),
                      mean=round(mu, 2), z_score=round(z, 2))
    return result

def tracker(metric_name: str, value: float) -> None:
    """Track a valuation metric for logging or monitoring purposes."""
    print(f"Tracking {metric_name}: {value}")
