import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ValuationMetrics:
    intrinsic_value: float
    relative_value: float
    technical_value: float
    confidence_score: float

class ValuationService:
    def __init__(self, data_service):
        self.data_service = data_service
        self.growth_rates = {}
        self.discount_rates = {}
        self.peer_multiples = {}

    async def get_comprehensive_valuation(self, symbol: str) -> ValuationMetrics:
        try:
            fundamental = await self._calculate_intrinsic_value(symbol)
            relative = await self._calculate_relative_value(symbol)
            technical = await self._calculate_technical_value(symbol)
            confidence = self._calculate_confidence_score(fundamental, relative, technical)
            
            return ValuationMetrics(
                intrinsic_value=fundamental,
                relative_value=relative,
                technical_value=technical,
                confidence_score=confidence
            )
        except Exception as e:
            logging.error(f"Valuation failed for {symbol}: {e}")
            return None

    async def _calculate_intrinsic_value(self, symbol: str) -> float:
        fundamentals = await self.data_service.get_fundamental_data(symbol)
        
        # DCF Calculation
        fcf = fundamentals.get('free_cash_flow', 0)
        growth_rate = self._estimate_growth_rate(fundamentals)
        discount_rate = self._calculate_discount_rate(fundamentals)
        
        return self._discounted_cash_flow(fcf, growth_rate, discount_rate)

    async def _calculate_relative_value(self, symbol: str) -> float:
        peers = await self._get_peer_group(symbol)
        multiples = await self._get_peer_multiples(peers)
        
        return self._calculate_fair_value_multiples(symbol, multiples)

    async def _calculate_technical_value(self, symbol: str) -> float:
        technicals = await self.data_service.get_market_indicators(symbol)
        
        # Combine multiple technical factors
        momentum = technicals.get('momentum', {})
        trend = self._analyze_price_trends(technicals)
        support_resistance = self._calculate_support_resistance(symbol)
        
        return self._weighted_technical_value(momentum, trend, support_resistance)

    def _estimate_growth_rate(self, fundamentals: Dict) -> float:
        historical_growth = fundamentals.get('historical_growth', 0.05)
        industry_growth = fundamentals.get('industry_growth', 0.03)
        analyst_estimates = fundamentals.get('growth_estimates', 0.04)
        
        weights = [0.4, 0.3, 0.3]
        return np.average([historical_growth, industry_growth, analyst_estimates], 
                         weights=weights)

    def _calculate_discount_rate(self, fundamentals: Dict) -> float:
        risk_free_rate = 0.03  # 10-year Treasury yield
        beta = fundamentals.get('beta', 1.0)
        market_risk_premium = 0.06
        
        return risk_free_rate + beta * market_risk_premium

    def _discounted_cash_flow(self, fcf: float, growth_rate: float, 
                            discount_rate: float, periods: int = 5) -> float:
        terminal_value = fcf * (1 + growth_rate)**periods / (discount_rate - growth_rate)
        dcf_value = 0
        
        for t in range(1, periods + 1):
            dcf_value += fcf * (1 + growth_rate)**t / (1 + discount_rate)**t
            
        return dcf_value + terminal_value / (1 + discount_rate)**periods

    def _calculate_confidence_score(self, fundamental: float, relative: float, 
                                 technical: float) -> float:
        # Weighted combination of valuation consistency
        values = [fundamental, relative, technical]
        std_dev = np.std(values)
        mean_value = np.mean(values)
        
        # Higher score for more consistent valuations
        consistency = 1 - min(std_dev / mean_value, 1) if mean_value != 0 else 0
        return float(consistency)
