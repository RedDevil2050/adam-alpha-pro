import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker
from backend.agents.technical.technical_utils import calculate_pivot_points, calculate_volume_profile

agent_name = "supertrend_agent"

async def run(symbol: str, multiplier: int = 3, period: int = 10) -> dict:
    cache_key = f"{agent_name}:{symbol}:{period}:{multiplier}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV data
    df = await fetch_ohlcv_series(symbol)
    if df is None or df.empty:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name
        }
    else:
        # Enhanced analysis
        pivot_points = calculate_pivot_points(df)
        volume_profile = calculate_volume_profile(df)
        
        # Original supertrend calculation
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        # ATR Calculation with volume weighting
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        
        volume_factor = df['volume'] / df['volume'].rolling(period).mean()
        atr = (tr.rolling(period).mean() * volume_factor).fillna(tr)
        
        # Final bands with pivot point validation
        hl2 = (high + low) / 2
        final_upperband = hl2 + (multiplier * atr)
        final_lowerband = hl2 - (multiplier * atr)
        
        # Trend strength with volume confirmation
        last_close = close.iloc[-1]
        volume_trend = df['volume'].pct_change().mean()
        
        # Enhanced verdict logic
        if last_close > final_upperband.iloc[-1] and volume_trend > 0:
            verdict = "STRONG_BUY"
            score = 1.0
        elif last_close < final_lowerband.iloc[-1] and volume_trend < 0:
            verdict = "STRONG_SELL"
            score = 0.0
        else:
            verdict = "NEUTRAL"
            score = 0.5

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(last_close, 2),
            "details": {
                "supertrend_upper": round(final_upperband.iloc[-1], 2),
                "supertrend_lower": round(final_lowerband.iloc[-1], 2),
                "pivot_points": {k: round(v, 2) for k, v in pivot_points.items()},
                "volume_trend": round(volume_trend, 4)
            },
            "score": score,
            "agent_name": agent_name
        }

    # 7) Cache result
    await redis_client.set(cache_key, result, ex=3600)
    # 8) Track progress
    tracker.update("technical", agent_name, "implemented")

    return result
