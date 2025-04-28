import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


def calculate_advanced_momentum(
    prices: pd.Series, volumes: pd.Series
) -> Dict[str, float]:
    """Advanced momentum indicators with volume confirmation"""
    roc = prices.pct_change(periods=20)
    vol_roc = volumes.pct_change(periods=20)

    # Money Flow Index
    typical_price = prices
    raw_money_flow = typical_price * volumes
    mfi = raw_money_flow.rolling(window=14).mean()

    # Volume Price Trend
    vpt = volumes * roc.fillna(0)

    return {
        "momentum": roc.iloc[-1],
        "volume_trend": vol_roc.iloc[-1],
        "mfi": mfi.iloc[-1],
        "vpt": vpt.sum(),
    }


def calculate_volatility_metrics(prices: pd.Series) -> Dict[str, float]:
    """Enhanced volatility analysis"""
    returns = prices.pct_change().dropna()
    parkinsons_volatility = np.sqrt(
        1 / (4 * np.log(2)) * (np.log(prices.high / prices.low) ** 2)
    ).mean()

    return {
        "std_dev": returns.std(),
        "parkinsons": parkinsons_volatility,
        "range_volatility": (prices.high - prices.low).mean() / prices.low.mean(),
    }
