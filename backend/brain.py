import numpy as np
from typing import Dict, List
from collections import deque
from backend.config.settings import settings


class Brain:
    """Core logic for market analysis and decision-making."""

    def __init__(self):
        self.history_window = deque(maxlen=settings.brain_smoothing_window)

    def process_data(self, data: List[float]) -> float:
        """Process incoming data and update the history window."""
        self.history_window.extend(data)
        return np.mean(self.history_window)

    def analyze(
        self, agent_results: Dict, market_regime: Dict, risk_metrics: Dict
    ) -> Dict:
        """Perform enhanced analysis using agent results, market regime, and risk metrics."""
        return analyze_results(agent_results, market_regime, risk_metrics)


def analyze_results(
    agent_results: Dict, market_regime: Dict, risk_metrics: Dict
) -> Dict:
    """Enhanced analysis incorporating regime and risk"""
    # Weight adjustments based on regime
    weights = {
        0: {"technical": 0.4, "fundamental": 0.4, "sentiment": 0.2},  # Low vol regime
        1: {"technical": 0.3, "fundamental": 0.5, "sentiment": 0.2},  # Medium vol
        2: {"technical": 0.2, "fundamental": 0.6, "sentiment": 0.2},  # High vol
    }

    current_weights = weights[market_regime["current_regime"]]

    # Risk-adjusted scoring
    risk_adjustment = 1 - abs(risk_metrics["var_95"])

    final_score = 0
    for category, weight in current_weights.items():
        category_score = np.mean([r["confidence"] for r in agent_results[category]])
        final_score += category_score * weight * risk_adjustment

    return {
        "score": final_score,
        "regime": market_regime,
        "risk_profile": risk_metrics,
        "weights_used": current_weights,
    }
