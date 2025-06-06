from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
import numpy as np
from loguru import logger
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, Any # Import Dict and Any
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "volume_spike_agent"
AGENT_CATEGORY = "technical"  # Define category for the decorator


class VolumeSpikeAgent(TechnicalAgent):
    # Ensure the main 'run' or calling method correctly uses _execute
    async def run(self, symbol: str, agent_outputs: dict = None) -> Dict:
         logger.debug(f"Running VolumeSpikeAgent for {symbol}")
         return await self._execute(symbol, agent_outputs if agent_outputs else {})

    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Define date range (e.g., last 60 days)
            end_date = datetime.today().date() # Correct usage
            start_date = end_date - relativedelta(months=7) # Use relativedelta

            # Fetch OHLCV data with start_date and end_date
            df = await fetch_ohlcv_series(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval='1d' # Assuming daily interval is needed
            )
            if df is None or df.empty:
                return self._error_response(symbol, "No data available")

            # Calculate volume metrics
            avg_volume = df["volume"].rolling(window=20).mean()
            volume_ratio = df["volume"] / avg_volume
            latest_ratio = volume_ratio.iloc[-1]

            # Determine if price moved with volume
            price_change = (df["close"].iloc[-1] - df["open"].iloc[-1]) / df[
                "open"
            ].iloc[-1]

            # Market regime context
            market_context = await self.get_market_context(symbol)
            regime = market_context.get("regime", "NEUTRAL")

            # Score and verdict logic
            if latest_ratio > 2.0:  # Volume spike detected
                if price_change > 0:
                    verdict = "BULLISH_VOLUME"
                    confidence = self.adjust_for_market_regime(0.8, regime)
                else:
                    verdict = "BEARISH_VOLUME"
                    confidence = self.adjust_for_market_regime(0.7, regime)
            else:
                verdict = "NORMAL_VOLUME"
                confidence = 0.5

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(latest_ratio, 2),
                "details": {
                    "volume_ratio": round(latest_ratio, 2),
                    "price_change": round(price_change * 100, 2),
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Volume spike calculation error: {e}")
            return self._error_response(symbol, str(e))

# Add standalone run function for backward compatibility with tests
@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY) # Use AGENT_CATEGORY
async def run(symbol: str, agent_outputs: dict = None, name: str = None, settings: Any = None, logger: Any = None, cache_client: Any = None, data_provider: Any = None, market_context_provider: Any = None) -> dict: # Added injected params
    """
    Standalone run function that creates and calls the VolumeSpikeAgent class.
    This maintains backward compatibility with tests that import this function.
    
    Args:
        symbol: The ticker symbol to analyze
        agent_outputs: Optional dictionary of outputs from other agents
        name: Injected by decorator
        settings: Injected by decorator
        logger: Injected by decorator
        cache_client: Injected by decorator
        data_provider: Injected by decorator
        market_context_provider: Injected by decorator
        
    Returns:
        Dictionary with the volume spike analysis results
    """
    # Pass all injected dependencies to the agent constructor
    agent = VolumeSpikeAgent(
        name=name,
        settings=settings,
        logger=logger,
        cache_client=cache_client,
        data_provider=data_provider,
        market_context_provider=market_context_provider
    )
    return await agent.run(symbol, agent_outputs)
