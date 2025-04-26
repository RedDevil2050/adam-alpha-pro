from backend.agents.market.base import MarketAgentBase
from backend.utils.data_provider import fetch_price_series
from backend.config.settings import settings
import numpy as np
import pandas as pd
from loguru import logger

agent_name = "correlation_agent"

class CorrelationAgent(MarketAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Get price data for symbol and market index
            symbol_prices = await fetch_price_series(symbol)
            market_symbol = settings.MARKET_INDEX or "^NSEI"
            market_prices = await fetch_price_series(market_symbol)
            
            if not symbol_prices or not market_prices or len(symbol_prices) < 60:
                return self._error_response(symbol, "Insufficient price history")

            # Calculate returns
            symbol_returns = pd.Series(symbol_prices).pct_change().dropna()
            market_returns = pd.Series(market_prices).pct_change().dropna()

            # Calculate rolling correlations
            correlation_30d = symbol_returns[-30:].corr(market_returns[-30:])
            correlation_60d = symbol_returns[-60:].corr(market_returns[-60:])
            
            # Calculate z-score of correlation change
            corr_change = correlation_30d - correlation_60d
            corr_zscore = (corr_change - np.mean(corr_change)) / np.std(corr_change) if np.std(corr_change) > 0 else 0

            # Determine regime based on correlation patterns
            if correlation_30d > 0.7 and corr_zscore > 1:
                verdict = "HIGH_CORRELATION"
                confidence = 0.9
            elif correlation_30d < 0.3 and corr_zscore < -1:
                verdict = "LOW_CORRELATION"
                confidence = 0.8
            else:
                verdict = "NORMAL_CORRELATION"
                confidence = 0.6

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(correlation_30d, 4),
                "details": {
                    "correlation_30d": round(correlation_30d, 4),
                    "correlation_60d": round(correlation_60d, 4),
                    "correlation_zscore": round(corr_zscore, 2),
                    "market_index": market_symbol
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Correlation calculation error: {e}")
            return self._error_response(symbol, str(e))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = CorrelationAgent()
    return await agent.execute(symbol, agent_outputs)
