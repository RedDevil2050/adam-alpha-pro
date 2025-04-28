from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StrategyConfig:
    name: str
    universe: List[str]
    parameters: Dict[str, any]
    risk_limits: Dict[str, float]


class StrategyManager:
    def __init__(self, data_service, risk_manager):
        self.data_service = data_service
        self.risk_manager = risk_manager
        self.active_strategies = {}
        self.strategy_performance = {}

    async def execute_strategy(self, config: StrategyConfig) -> Dict[str, any]:
        try:
            signals = await self._generate_signals(config)
            risk_adjusted = self.risk_manager.adjust_positions(signals)
            return await self._optimize_execution(risk_adjusted)
        except Exception as e:
            logging.error(f"Strategy execution failed: {e}")
            return {}

    async def _generate_signals(self, config: StrategyConfig) -> Dict[str, float]:
        data = await self.data_service.get_market_data(config.universe)
        return {
            symbol: self._apply_strategy_rules(data[symbol], config.parameters)
            for symbol in config.universe
        }
