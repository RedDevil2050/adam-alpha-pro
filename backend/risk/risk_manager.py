import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class RiskLimits:
    max_position_size: float
    max_portfolio_var: float
    max_leverage: float
    concentration_limit: float


class RiskManager:
    def __init__(self, data_service):
        self.data_service = data_service
        self.risk_limits = RiskLimits(
            max_position_size=0.1,
            max_portfolio_var=0.2,
            max_leverage=2.0,
            concentration_limit=0.25,
        )

    async def validate_trades(self, trades: List[Dict]) -> Dict[str, any]:
        try:
            position_risk = await self._calculate_position_risk(trades)
            portfolio_risk = await self._calculate_portfolio_risk(trades)
            leverage_check = self._check_leverage_limits(trades)

            validation = {
                "position_check": position_risk <= self.risk_limits.max_position_size,
                "portfolio_check": portfolio_risk <= self.risk_limits.max_portfolio_var,
                "leverage_check": leverage_check,
            }

            return {"approved": all(validation.values()), "checks": validation}
        except Exception as e:
            logging.error(f"Risk validation failed: {e}")
            return {"approved": False, "error": str(e)}
