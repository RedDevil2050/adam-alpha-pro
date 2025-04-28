from typing import Dict, Optional, Tuple
import numpy as np
from datetime import datetime, time
import pandas as pd
from loguru import logger


class MarketDataValidator:
    def __init__(self):
        self.market_hours = {"open": time(9, 15), "close": time(15, 30)}
        self.price_limits = {"max_change": 0.20}  # 20% max price change

    def validate_price_data(self, data: Dict) -> Tuple[bool, Optional[str]]:
        try:
            # Check for stale data
            timestamp = pd.to_datetime(data.get("timestamp"))
            if (datetime.now() - timestamp).total_seconds() > 300:  # 5 min stale
                return False, "Stale data detected"

            # Check for price anomalies
            if self._detect_price_anomaly(
                data.get("price"), data.get("previous_close")
            ):
                return False, "Price anomaly detected"

            # Check market hours
            if not self._is_market_hours():
                return False, "Outside market hours"

            return True, None
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, str(e)

    def _detect_price_anomaly(self, price: float, prev_close: float) -> bool:
        if not price or not prev_close:
            return True
        return abs(price - prev_close) / prev_close > self.price_limits["max_change"]

    def _is_market_hours(self) -> bool:
        now = datetime.now().time()
        return self.market_hours["open"] <= now <= self.market_hours["close"]
