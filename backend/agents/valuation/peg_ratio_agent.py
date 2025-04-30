import asyncio
from backend.utils.data_provider import fetch_company_info # Use unified provider
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator
from backend.config.settings import get_settings  # Added import

agent_name = "peg_ratio_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # 1. Get PE Ratio from pe_ratio_agent output if available
    pe_ratio = None
    pe_source = "N/A"
    if agent_outputs and symbol in agent_outputs and "pe_ratio_agent" in agent_outputs[symbol]:
        pe_data = agent_outputs[symbol]["pe_ratio_agent"]
        if pe_data and "value" in pe_data and isinstance(pe_data["value"], (int, float)):
            pe_ratio = pe_data["value"]
            pe_source = "pe_ratio_agent"
            logger.debug(f"[{agent_name}] Using PE Ratio {pe_ratio} from pe_ratio_agent for {symbol}")

    # 2. Fetch Company Info for Growth Rate (and PE if not from agent)
    company_info = await fetch_company_info(symbol)

    if not company_info:
        logger.warning(f"[{agent_name}] Could not fetch company info for {symbol}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Could not fetch company info"},
            "agent_name": agent_name,
        }

    # 3. Get Analyst Target Price (often includes growth estimates) or specific growth fields
    # Alpha Vantage OVERVIEW often has 'AnalystTargetPrice', sometimes growth fields directly.
    # Let's prioritize 'EPSGrowthRate5Years' if available, else try parsing from other fields.
    # This part is highly dependent on the actual fields returned by fetch_company_info
    # Adjust the keys based on provider output. Example keys:
    growth_rate_str = company_info.get("EPSGrowthRate5Years") # Example key
    if not growth_rate_str:
         growth_rate_str = company_info.get("EstimatedGrowthRate") # Another example

    growth_rate = None
    if growth_rate_str and growth_rate_str.lower() not in ["none", "-", ""]:
        try:
            # Growth rate might be percentage, remove '%' if present
            growth_rate = float(growth_rate_str.replace('%', ''))
            # If PE wasn't obtained from agent, try getting it from company_info
            if pe_ratio is None:
                pe_ratio_str = company_info.get("PERatio")
                if pe_ratio_str and pe_ratio_str.lower() not in ["none", "-", ""]:
                    pe_ratio = float(pe_ratio_str)
                    pe_source = "company_info"

        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse growth rate ('{growth_rate_str}') or PE ('{company_info.get('PERatio')}') for {symbol}"
            )
            # Continue without growth rate if PE is available, or return error
            if pe_ratio is None:
                 return {
                    "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
                    "details": {"reason": "Could not parse PE Ratio or Growth Rate"}, "agent_name": agent_name,
                 }
            # else: proceed to calculate PEG=infinity if growth is zero/negative later

    # 4. Validate PE and Growth Rate
    if pe_ratio is None or growth_rate is None:
        missing = []
        if pe_ratio is None: missing.append("PE Ratio")
        if growth_rate is None: missing.append("EPS Growth Rate")
        reason = f"Missing required data: {', '.join(missing)}"
        logger.warning(f"[{agent_name}] {reason} for {symbol}")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "pe_source": pe_source}, "agent_name": agent_name,
        }

    if pe_ratio <= 0:
        logger.info(f"[{agent_name}] PE Ratio is zero or negative ({pe_ratio}) for {symbol}. Cannot calculate PEG.")
        return {
            "symbol": symbol, "verdict": "NOT_APPLICABLE", "confidence": 0.8, "value": None,
            "details": {"reason": "PE Ratio is zero or negative", "pe_ratio": pe_ratio, "growth_rate": growth_rate, "pe_source": pe_source},
            "agent_name": agent_name,
        }

    if growth_rate <= 0:
        logger.info(f"[{agent_name}] Growth rate is zero or negative ({growth_rate}) for {symbol}. PEG is not meaningful.")
        # You could return a very high PEG or a specific verdict
        return {
            "symbol": symbol, "verdict": "LOW_OR_NEG_GROWTH", "confidence": 0.8, "value": float('inf'), # Or None
            "details": {"reason": "Growth rate is zero or negative", "pe_ratio": pe_ratio, "growth_rate": growth_rate, "pe_source": pe_source},
            "agent_name": agent_name,
        }

    # 5. Calculate PEG Ratio
    peg_ratio = pe_ratio / growth_rate

    # 6. Determine Verdict (Example thresholds)
    # Example verdict logic based on PEG ratio
    if peg_ratio < 1:
        verdict = "UNDERVALUED"
        confidence = 0.9
    elif 1 <= peg_ratio <= 2:
        verdict = "FAIR_VALUE"
        confidence = 0.7
    else:
        verdict = "OVERVALUED"
        confidence = 0.6

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(peg_ratio, 4),
        "details": {
            "peg_ratio": round(peg_ratio, 4),
            "pe_ratio": round(pe_ratio, 4),
            "growth_rate_pct": round(growth_rate, 4),
            "pe_source": pe_source,
            "data_source": "alpha_vantage_overview", # Or adjust based on actual provider
        },
        "agent_name": agent_name,
    }
