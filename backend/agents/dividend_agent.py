import logging
import asyncio
from typing import Dict, Any, Optional, List, Union

from backend.utils.data_provider import fetch_eps_data, fetch_market_data
from backend.utils.retry_utils import async_retry
from backend.agents.base import AgentBase

logger = logging.getLogger(__name__)

agent_name = "dividend_agent" # Added for discovery

class DividendAgent(AgentBase):
    """
    Agent that analyzes dividend yields and related metrics to make investment recommendations.

    This agent fetches real-world dividend data and evaluates stocks based on:
    1. Current dividend yield
    2. Dividend payout ratio
    3. Dividend growth history (when available)
    4. Dividend sustainability
    """

    async def _execute(self, symbol: str, agent_outputs: dict = None) -> dict:
        # agent_name is now defined at module level
        logger.debug(f"{agent_name} executing for {symbol}")

        try:
            # Fetch detailed EPS and dividend data
            eps_data = await fetch_eps_data(symbol)
            logger.debug(f"Fetched EPS data for {symbol}: {eps_data}")

            # Extract key metrics
            dividend_yield = eps_data.get("dividend_yield", 0)
            price = eps_data.get("price", 0.0)
            eps = eps_data.get("eps", 0.0)
            pe_ratio = eps_data.get("pe_ratio", 0.0)

            # Check for presence of dividend - some stocks don't pay dividends
            if dividend_yield is None or dividend_yield == 0:
                return {
                    "symbol": symbol,
                    "verdict": "HOLD",
                    "confidence": 50.0,
                    "value": 0,
                    "details": {
                        "dividend_yield": 0,
                        "reason": "No dividend data available or stock does not pay dividends",
                    },
                    "error": None,
                    "agent_name": agent_name,
                }

            # Calculate dividend payout ratio if EPS is available
            payout_ratio = None
            if eps and eps > 0 and dividend_yield > 0 and price > 0:
                annual_dividend = price * dividend_yield
                payout_ratio = (annual_dividend / eps) * 100

            # Analyze dividend metrics
            details = {
                "dividend_yield": dividend_yield,
                "price": price,
                "annual_dividend": (
                    price * dividend_yield if price and dividend_yield else None
                ),
                "eps": eps,
                "pe_ratio": pe_ratio,
                "payout_ratio": payout_ratio,
            }

            # Evaluate dividend investment quality
            value = dividend_yield  # Base value is the yield itself

            # Determine verdict based on multiple factors
            verdict = "HOLD"  # Default

            # Basic yield evaluation - higher yields get more interest
            if dividend_yield >= 0.05:  # 5%+ yield
                verdict = "BUY"
            elif dividend_yield >= 0.03:  # 3%+ yield
                verdict = "HOLD"

            # Factor in payout ratio if available - avoid unsustainable dividends
            if payout_ratio is not None:
                if payout_ratio > 100:  # Paying more than earnings
                    details["warning"] = (
                        "Dividend may not be sustainable (payout ratio > 100%)"
                    )
                    verdict = "HOLD" if verdict == "BUY" else "HOLD"
                elif payout_ratio > 80:  # High but still below 100%
                    details["note"] = "High payout ratio (>80%)"

                # Preferred range for payout ratios
                if 30 <= payout_ratio <= 60:
                    details["positive"] = "Healthy payout ratio (30-60%)"
                    if verdict == "HOLD" and dividend_yield >= 0.025:
                        verdict = "BUY"

            # Set confidence based on the quality of data and analysis
            confidence_factors = []

            # Yield-based confidence
            if dividend_yield > 0:
                yield_confidence = min(dividend_yield * 1000, 90)  # Cap at 90
                confidence_factors.append(yield_confidence)

            # Data quality confidence
            data_points = sum(
                1
                for v in [dividend_yield, price, eps, pe_ratio, payout_ratio]
                if v is not None
            )
            data_quality = (
                data_points / 5
            ) * 100  # Percentage of data points available
            confidence_factors.append(data_quality)

            # Calculate overall confidence
            confidence = (
                sum(confidence_factors) / len(confidence_factors)
                if confidence_factors
                else 50.0
            )

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": value,
                "details": details,
                "error": None,
                "agent_name": agent_name,
            }
        except Exception as e:
            logger.error(f"Error in DividendAgent for {symbol}: {e}")
            return {
                "symbol": symbol,
                "verdict": "ERROR",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": str(e),
                "agent_name": agent_name,
            }
