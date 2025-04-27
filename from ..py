from ..base import AgentBase
from ...utils.data_provider import fetch_market_data
from ...monitoring.metrics import metrics_collector
import numpy as np

class PriceTargetAgent(AgentBase):
    def __init__(self):
        super().__init__(category="intelligence")
        
    async def analyze(self, symbol: str) -> dict:
        try:
            # Fetch data
            market_data = await fetch_market_data(symbol)
            analyst_targets = await self._fetch_analyst_targets(symbol)
            
            if not analyst_targets:
                # Calculate based on technical indicators if no analyst targets
                target = await self._calculate_technical_target(market_data)
                confidence = 0.6
            else:
                target = np.median(analyst_targets)
                confidence = 0.8
            
            current_price = market_data['price']
            potential = ((target - current_price) / current_price) * 100
            
            return {
                'price_target': target,
                'potential': potential,
                'confidence': confidence,
                'score': self._calculate_score(potential)
            }
            
        except Exception as e:
            metrics_collector.agent_errors.labels(
                agent="PriceTargetAgent",
                error=str(e)
            ).inc()
            raise
            
    def _calculate_score(self, potential: float) -> float:
        # Convert potential return to 0-100 score
        return min(max(50 + (potential * 2), 0), 100)
