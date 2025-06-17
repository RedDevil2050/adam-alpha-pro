import numpy as np
from typing import Dict, List


class BollingerBandAgent:
    """Agent to calculate Bollinger Bands for a given symbol."""

    def __init__(self, window: int = 20, num_std_dev: float = 2.0):
        self.window = window
        self.num_std_dev = num_std_dev

    def calculate(self, prices: List[float]) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        if len(prices) < self.window:
            raise ValueError("Not enough data to calculate Bollinger Bands")

        mean = np.mean(prices[-self.window :])
        std_dev = np.std(prices[-self.window :])

        return {
            "upper_band": mean + self.num_std_dev * std_dev,
            "lower_band": mean - self.num_std_dev * std_dev,
            "mean": mean,
        }


def run(prices: List[float], agent_outputs: dict = None) -> Dict[str, float]:
    """Run the Bollinger Band calculation."""
    agent = BollingerBandAgent()
    return agent.calculate(prices)
