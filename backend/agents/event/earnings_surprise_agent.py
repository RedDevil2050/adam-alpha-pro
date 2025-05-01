import asyncio
from backend.utils.data_provider import fetch_earnings_calendar # Assuming this function exists
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings
from datetime import datetime, timedelta
import numpy as np

agent_name = "earnings_surprise_agent"
AGENT_CATEGORY = "event"

@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=86400 # Cache for a day
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Analyzes recent earnings reports for surprises compared to analyst estimates.

    Purpose:
        Identifies significant deviations (surprises) between reported Earnings Per Share (EPS)
        and estimated EPS for the most recent earnings announcement.

    Metrics Calculated:
        - Earnings Surprise Percentage = ((Actual EPS - Estimated EPS) / abs(Estimated EPS)) * 100

    Logic:
        1. Fetches recent earnings calendar data for the symbol (e.g., last 90 days).
        2. Filters for the most recent earnings report with both actual and estimated EPS.
        3. If no suitable report is found, returns 'NO_RECENT_EARNINGS'.
        4. If estimated EPS is zero or very close to zero, returns 'ESTIMATE_NEAR_ZERO' as percentage surprise is unreliable.
        5. Calculates the earnings surprise percentage.
        6. Determines a verdict based on the surprise percentage:
            - 'POSITIVE_SURPRISE': Surprise > threshold (e.g., 5%).
            - 'NEGATIVE_SURPRISE': Surprise < -threshold (e.g., -5%).
            - 'IN_LINE': Surprise is within the threshold.
        7. Sets confidence based on the magnitude of the surprise.

    Dependencies:
        - Requires earnings calendar data including report date, actual EPS, and estimated EPS
          (`fetch_earnings_calendar`).

    Configuration Used (from settings.py -> AgentSettings -> EarningsSurpriseAgentSettings):
        - `SURPRISE_THRESHOLD_PCT`: Percentage threshold to define a significant surprise (default 5.0).

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'POSITIVE_SURPRISE', 'NEGATIVE_SURPRISE', 'IN_LINE', 'NO_RECENT_EARNINGS', 'ESTIMATE_NEAR_ZERO'.
        - confidence (float): Confidence score (0.0 to 1.0).
        - value (float | None): The calculated surprise percentage.
        - details (dict): Contains actual EPS, estimated EPS, report date, and threshold used.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred.
    """
    settings = get_settings()
    # Use .get for nested attribute access with fallback
    surprise_settings = settings.agent_settings.get("earnings_surprise", MagicMock())
    threshold_pct = getattr(surprise_settings, 'SURPRISE_THRESHOLD_PCT', 5.0) # Default 5%

    # Fetch recent earnings data (e.g., last 90 days)
    try:
        # Assuming fetch_earnings_calendar returns a list of dicts sorted by date descending
        # Each dict should have keys like 'reportDate', 'actualEPS', 'estimatedEPS'
        earnings_data = await fetch_earnings_calendar(symbol, lookback_days=90)
    except Exception as e:
        logger.error(f"[{agent_name}] Error fetching earnings data for {symbol}: {e}")
        return {
            "symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
            "details": {"reason": f"Failed to fetch earnings data: {e}"}, "agent_name": agent_name,
        }

    if not earnings_data:
        logger.info(f"[{agent_name}] No earnings data found for {symbol} in the lookback period.")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "No earnings data found"}, "agent_name": agent_name,
        }

    # Find the most recent report with both actual and estimated EPS
    latest_report = None
    for report in earnings_data:
        if report.get('actualEPS') is not None and report.get('estimatedEPS') is not None:
            try:
                # Validate data types
                actual_eps = float(report['actualEPS'])
                estimated_eps = float(report['estimatedEPS'])
                report_date = report.get('reportDate') # Keep as string or parse if needed
                latest_report = {
                    "actual": actual_eps,
                    "estimated": estimated_eps,
                    "date": report_date
                }
                break # Found the most recent valid report
            except (ValueError, TypeError):
                logger.warning(f"[{agent_name}] Invalid EPS data types in report for {symbol}: {report}")
                continue # Skip this report

    if latest_report is None:
        logger.info(f"[{agent_name}] No recent earnings report with actual and estimated EPS found for {symbol}.")
        return {
            "symbol": symbol, "verdict": "NO_RECENT_EARNINGS", "confidence": 0.0, "value": None,
            "details": {"reason": "No recent report found with actual and estimated EPS"},
            "agent_name": agent_name,
        }

    actual = latest_report['actual']
    estimated = latest_report['estimated']

    # Handle near-zero estimate to avoid division issues and meaningless percentages
    if abs(estimated) < 1e-6:
        logger.info(f"[{agent_name}] Estimated EPS is near zero ({estimated}) for {symbol}. Surprise calculation unreliable.")
        # Determine verdict based on actual vs zero estimate
        if actual > 1e-6:
            verdict = "POSITIVE_SURPRISE" # Beat zero estimate
            confidence = 0.6
        elif actual < -1e-6:
            verdict = "NEGATIVE_SURPRISE" # Missed zero estimate
            confidence = 0.6
        else:
            verdict = "IN_LINE" # Met zero estimate
            confidence = 0.5
        return {
            "symbol": symbol, "verdict": verdict, "confidence": confidence, "value": None, # No percentage value
            "details": {
                "reason": "Estimated EPS near zero",
                "actual_eps": actual,
                "estimated_eps": estimated,
                "report_date": latest_report['date']
            },
            "agent_name": agent_name,
        }

    # Calculate surprise percentage
    surprise_pct = ((actual - estimated) / abs(estimated)) * 100

    # Determine verdict based on threshold
    if surprise_pct > threshold_pct:
        verdict = "POSITIVE_SURPRISE"
        # Confidence scales with surprise magnitude (capped)
        confidence = min(0.95, 0.6 + (surprise_pct / (threshold_pct * 5))) # Example scaling
    elif surprise_pct < -threshold_pct:
        verdict = "NEGATIVE_SURPRISE"
        confidence = min(0.95, 0.6 + (abs(surprise_pct) / (threshold_pct * 5))) # Example scaling
    else:
        verdict = "IN_LINE"
        confidence = 0.5 # Lower confidence for in-line results

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(surprise_pct, 2),
        "details": {
            "actual_eps": actual,
            "estimated_eps": estimated,
            "report_date": latest_report['date'],
            "surprise_pct": round(surprise_pct, 2),
            "threshold_pct": threshold_pct
        },
        "agent_name": agent_name,
    }
