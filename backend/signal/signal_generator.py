import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from scipy.stats import zscore
from datetime import datetime, timedelta

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
                signal = self._evaluate_signal_conditions(symbol, analytics, market_state)
                if signal.confidence >= self.minimum_confidence:
                    signals.append(signal)
            
            return signals
        except Exception as e:
            logging.error(f"Signal generation failed: {e}")
            return []

    def _evaluate_signal_conditions(self, symbol: str, 
                                 analytics: Dict, 
                                 market_state: MarketState) -> TradingSignal:
        technical_score = self._calculate_technical_score(analytics)
        regime_score = self._calculate_regime_score(market_state)
        
        direction = 'long' if technical_score > 0 else 'short'
        strength = abs(technical_score)
        confidence = self._calculate_signal_confidence(technical_score, regime_score)
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            timestamp=pd.Timestamp.now()
        )

    async def _calculate_technical_score(self, analytics: Dict) -> float:
        momentum = analytics.get('momentum', {})
        trend = analytics.get('trend', {})
        
        weights = {
            'rsi': 0.2,
            'macd': 0.3,
            'trend_strength': 0.3,
            'volume_trend': 0.2
        }
        
        return sum(weights[k] * momentum.get(k, 0) for k in weights)

    def _calculate_regime_score(self, market_state: MarketState) -> float:
        regime_weights = {
            'normal': 1.0,
            'stress': 0.5,
            'crisis': 0.0,
            'recovery': 0.75
        }
        return regime_weights.get(market_state.regime, 0.0)

    def _calculate_signal_confidence(self, technical_score: float, regime_score: float) -> float:
        signal_strength = abs(technical_score)
        market_quality = self._assess_market_quality()
        
        return min(signal_strength * regime_score * market_quality, 1.0)

    def _assess_market_quality(self) -> float:
        recent_signals = self._get_recent_signals()
        accuracy = self._calculate_signal_accuracy(recent_signals)
        return accuracy if accuracy > 0.5 else 0.5
