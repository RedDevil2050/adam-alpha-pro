\
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Dict, Optional
import datetime

class VerdictType(Enum):
    BUY_OVERSOLD_CROSS = "BUY_OVERSOLD_CROSS"
    SELL_OVERBOUGHT_CROSS = "SELL_OVERBOUGHT_CROSS"
    HOLD_NEUTRAL = "HOLD_NEUTRAL"
    BUY_CROSS_BELOW_50 = "BUY_CROSS_BELOW_50"
    HOLD_BULLISH_CROSS_UPPER = "HOLD_BULLISH_CROSS_UPPER"
    SELL_CROSS_ABOVE_50 = "SELL_CROSS_ABOVE_50"
    HOLD_BEARISH_CROSS_LOWER = "HOLD_BEARISH_CROSS_LOWER"
    # Add other potential verdict types as needed by other agents or common usage
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    NO_DATA = "NO_DATA"
    ERROR = "ERROR"

@dataclass
class DataPoint:
    timestamp: datetime.datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: Optional[int] = None

@dataclass
class TimeSeriesData:
    data: List[DataPoint]
    symbol: Optional[str] = None
    interval: Optional[str] = None

@dataclass
class Verdict:
    agent_name: str
    verdict_type: VerdictType
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    value: Optional[Any] = None # For specific value like K-D difference, or raw score
    # score: Optional[float] = None # Raw score before calibration, if needed

# Placeholder for AgentContext if it's truly a distinct model.
# However, AgentBase now provides self.settings and self.context (dict)
# and self.get_market_context()
# If a specific typed context object is still desired across agents, define it here.
# For now, we'll rely on AgentBase's provisions.

# MarketRegime is now string-based as observed. If an Enum is still needed for other purposes,
# it could be defined here, but the stochastic agent will use string values.
# class MarketRegime(Enum):
#     BULLISH = "BULL" # Or "BULLISH"
#     BEARISH = "BEAR" # Or "BEARISH"
#     NEUTRAL = "NEUTRAL"
#     VOLATILE = "VOLATILE"
#     UNKNOWN = "UNKNOWN"
