from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
import pandas as pd
import numpy as np
from loguru import logger

agent_name = "supertrend_agent"


class SupertrendAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            df = await fetch_ohlcv_series(symbol)
            if df is None or df.empty:
                return self._error_response(symbol, "No data available")

            # Get market context for volatility adjustment
            market_context = await self.get_market_context(symbol)
            volatility = market_context.get("volatility", 0.2)
            adjustments = self.get_volatility_adjustments(volatility)

            # Calculate Supertrend with adjusted parameters
            period = int(10 * adjustments["period_adj"])
            multiplier = 3.0 * adjustments["signal_mult"]

            # ATR Calculation
            df["tr"] = pd.DataFrame(
                {
                    "hl": df["high"] - df["low"],
                    "hc": abs(df["high"] - df["close"].shift(1)),
                    "lc": abs(df["low"] - df["close"].shift(1)),
                }
            ).max(axis=1)

            df["atr"] = df["tr"].rolling(period).mean()

            # Supertrend bands
            hl2 = (df["high"] + df["low"]) / 2
            df["upper_band"] = hl2 + multiplier * df["atr"]
            df["lower_band"] = hl2 - multiplier * df["atr"]

            # Initialize Supertrend
            df["supertrend"] = df["upper_band"]
            df["uptrend"] = True

            # Calculate Supertrend direction
            for i in range(period, len(df)):
                curr, prev = df.iloc[i], df.iloc[i - 1]

                if curr["close"] > prev["upper_band"]:
                    df.loc[df.index[i], "uptrend"] = True
                elif curr["close"] < prev["lower_band"]:
                    df.loc[df.index[i], "uptrend"] = False
                else:
                    df.loc[df.index[i], "uptrend"] = prev["uptrend"]

                if df.loc[df.index[i], "uptrend"]:
                    df.loc[df.index[i], "supertrend"] = df.loc[
                        df.index[i], "lower_band"
                    ]
                else:
                    df.loc[df.index[i], "supertrend"] = df.loc[
                        df.index[i], "upper_band"
                    ]

            # Generate signals
            current_price = df["close"].iloc[-1]
            current_supertrend = df["supertrend"].iloc[-1]
            is_uptrend = df["uptrend"].iloc[-1]

            regime = market_context.get("regime", "NEUTRAL")

            if is_uptrend and current_price > current_supertrend:
                verdict = "BUY"
                confidence = self.adjust_for_market_regime(0.8, regime)
            elif not is_uptrend and current_price < current_supertrend:
                verdict = "SELL"
                confidence = self.adjust_for_market_regime(0.7, regime)
            else:
                verdict = "HOLD"
                confidence = 0.5

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(current_supertrend, 2),
                "details": {
                    "current_price": round(current_price, 2),
                    "supertrend": round(current_supertrend, 2),
                    "is_uptrend": is_uptrend,
                    "atr": round(df["atr"].iloc[-1], 2),
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Supertrend calculation error: {e}")
            return self._error_response(symbol, str(e))


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = SupertrendAgent()
    return await agent.execute(symbol, agent_outputs)
