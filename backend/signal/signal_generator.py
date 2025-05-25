import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from scipy.stats import zscore
from datetime import datetime, timedelta
import logging
from backend.analysis.market_analyzer import MarketState


@dataclass
class TradingSignal:
    symbol: str
    direction: str
    strength: float
    confidence: float
    timestamp: pd.Timestamp


class SignalGenerator:
    def __init__(self, market_analyzer, data_service):
        self.market_analyzer = market_analyzer
        self.data_service = data_service
        self.signal_history = {}
        self.minimum_confidence = 0.6

    async def generate_signals(self, symbols: List[str]) -> List[TradingSignal]:
        try:
            market_state = await self.market_analyzer.analyze_market_state(symbols)
            signals = []

            for symbol in symbols:
                analytics = await self.data_service.get_advanced_analytics(symbol)
                signal = self._evaluate_signal_conditions(
                    symbol, analytics, market_state
                )
                if signal.confidence >= self.minimum_confidence:
                    signals.append(signal)
                    # Store signal in history
                    if symbol not in self.signal_history:
                        self.signal_history[symbol] = []
                    self.signal_history[symbol].append(signal)
                    # Optional: Trim history to save memory, e.g., keep last 100 signals per symbol
                    # self.signal_history[symbol] = self.signal_history[symbol][-100:]

            return signals
        except Exception as e:
            logging.error(f"Signal generation failed: {e}")
            return []

    def _evaluate_signal_conditions(
        self, symbol: str, analytics: Dict, market_state: MarketState
    ) -> TradingSignal:
        technical_score = self._calculate_technical_score(analytics)
        regime_score = self._calculate_regime_score(market_state)

        direction = "long" if technical_score > 0 else "short"
        strength = abs(technical_score)
        confidence = self._calculate_signal_confidence(technical_score, regime_score)

        return TradingSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            timestamp=pd.Timestamp.now(),
        )

    async def _calculate_technical_score(self, analytics: Dict) -> float:
        momentum = analytics.get("momentum", {})
        trend = analytics.get("trend", {})

        weights = {"rsi": 0.2, "macd": 0.3, "trend_strength": 0.3, "volume_trend": 0.2}

        return sum(weights[k] * momentum.get(k, 0) for k in weights)

    def _calculate_regime_score(self, market_state: MarketState) -> float:
        regime_weights = {"normal": 1.0, "stress": 0.5, "crisis": 0.0, "recovery": 0.75}
        return regime_weights.get(market_state.regime, 0.0)

    def _calculate_signal_confidence(
        self, technical_score: float, regime_score: float
    ) -> float:
        signal_strength = abs(technical_score)
        market_quality = self._assess_market_quality()

        return min(signal_strength * regime_score * market_quality, 1.0)

    def _get_recent_signals(self, lookback_days: int = 7) -> List[TradingSignal]:
        """
        Retrieves all signals generated across all symbols within the recent lookback period.
        """
        all_recent_signals = []
        cutoff_date = pd.Timestamp.now(tz='UTC') - timedelta(days=lookback_days) # Ensure timezone awareness
        for symbol_signals in self.signal_history.values():
            for signal in symbol_signals:
                # Ensure signal.timestamp is timezone-aware or convert appropriately
                signal_ts = signal.timestamp
                if not signal_ts.tzinfo:
                    signal_ts = signal_ts.tz_localize('UTC') # Assuming signals are stored in UTC

                if signal_ts >= cutoff_date:
                    all_recent_signals.append(signal)
        return all_recent_signals

    def _calculate_signal_accuracy(self, recent_signals: List[TradingSignal]) -> float:
        """
        Placeholder for calculating the accuracy of recent signals.
        A real implementation would compare signal predictions with actual market outcomes.
        """
        if not recent_signals:
            return 0.5  # Neutral accuracy if no recent signals to assess

        # --- Placeholder Logic ---
        # This is a critical part of the system and needs a robust implementation.
        # For now, it returns a default optimistic value.
        # You should replace this with logic that:
        # 1. Fetches historical price data for the period following each signal.
        # 2. Defines criteria for a "successful" signal (e.g., price moved in predicted direction by X%).
        # 3. Calculates the ratio of successful signals to total signals.
        logging.warning(
            "SignalGenerator._calculate_signal_accuracy is using a placeholder implementation. "
            "Actual accuracy calculation logic needs to be implemented."
        )
        # Example: If there are signals, assume a default accuracy.
        # This could be made more sophisticated even as a placeholder, e.g., based on number of signals.
        return 0.6  # Default placeholder accuracy

    def _assess_market_quality(self) -> float:
        recent_signals = self._get_recent_signals()
        accuracy = self._calculate_signal_accuracy(recent_signals)
        return accuracy if accuracy > 0.5 else 0.5
