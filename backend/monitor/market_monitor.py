import numpy as np
import pandas as pd
from typing import Dict, List
import asyncio
import logging
from dataclasses import dataclass


@dataclass
class MarketAlert:
    level: str
    message: str
    timestamp: datetime
    action_required: bool


class MarketMonitor:
    def __init__(self, data_service, market_analyzer):
        self.data_service = data_service
        self.market_analyzer = market_analyzer
        self.alert_history = []
        self.monitoring = False

    async def start_monitoring(self, symbols: List[str]):
        self.monitoring = True
        while self.monitoring:
            try:
                await self._check_market_conditions(symbols)
                await self._monitor_signal_quality()
                await self._check_risk_levels()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logging.error(f"Market monitoring error: {e}")

    async def _check_market_conditions(self, symbols: List[str]):
        state = await self.market_analyzer.analyze_market_state(symbols)
        if state.regime in ["stress", "crisis"]:
            self._generate_alert(
                "high", f"Market regime changed to {state.regime}", True
            )
