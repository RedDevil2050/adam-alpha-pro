import datetime
from collections import deque
from backend.config.settings import settings

# Define regime-specific weights
HIGH_VOL_WEIGHTS = {
    "valuation": 0.25,
    "technical": 0.10,
    "sentiment": 0.05,
    "esg": 0.10,
    "risk": 0.30,
    "event": 0.10,
    "macro": 0.10
}
LOW_VOL_WEIGHTS = {
    "valuation": 0.20,
    "technical": 0.25,
    "sentiment": 0.10,
    "esg": 0.10,
    "risk": 0.10,
    "event": 0.10,
    "macro": 0.15
}

_history_window = deque(maxlen=settings.brain_smoothing_window)

def aggregate_scores(category_results: dict) -> float:
    """
    Aggregate scores from each category using confidence-weighting,
    regime-adaptive weights, and temporal smoothing.
    """
    # 1) Compute per-category score weighted by agent confidences
    cat_score = {}
    for cat, agents in category_results.items():
        scores = [r.get('score', 0.0) for r in agents]
        confs = [r.get('confidence', 0.0) for r in agents]
        total_conf = sum(confs) if sum(confs) > 0 else 1.0
        weighted = sum(s * c for s, c in zip(scores, confs)) / total_conf
        cat_score[cat] = weighted

    # 2) Regime detection via volatility agent
    vol_list = [r.get('value') for r in category_results.get('risk', []) if r.get('agent_name') == 'volatility_agent']
    vol = vol_list[0] if vol_list else None
    if vol is not None and vol > settings.vol_threshold:
        weights = HIGH_VOL_WEIGHTS
    else:
        weights = LOW_VOL_WEIGHTS

    # 3) Final aggregation
    final = sum(weights.get(cat, 0.0) * cat_score.get(cat, 0.0) for cat in cat_score)

    # 4) Temporal smoothing
    _history_window.append(final)
    smoothed = sum(_history_window) / len(_history_window)

    return smoothed

def make_verdict(score: float) -> str:
    """
    Translate a normalized score into a discrete verdict.
    """
    if score >= 0.7:
        return "STRONG_BUY"
    if score >= 0.5:
        return "BUY"
    if score >= 0.3:
        return "HOLD"
    if score >= 0.1:
        return "AVOID"
    return "STRONG_AVOID"
