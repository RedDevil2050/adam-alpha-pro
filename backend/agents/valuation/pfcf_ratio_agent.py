import asyncio
from backend.utils.data_provider import fetch_company_info, fetch_cash_flow_data # Updated imports
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator
import math  # Import math for isnan

agent_name = "pfcf_ratio_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data (contains Market Cap) and Cash Flow data (contains FCF components)
    # P/FCF = Market Cap / Free Cash Flow
    # FCF = Operating Cash Flow - Capital Expenditures
    overview_data_task = fetch_company_info(symbol) # Use fetch_company_info
    cash_flow_data_task = fetch_cash_flow_data(symbol) # Use fetch_cash_flow_data

    overview_data, cash_flow_data = await asyncio.gather(overview_data_task, cash_flow_data_task)


    if not overview_data or not cash_flow_data:
        missing_data = []
        if not overview_data:
            missing_data.append("company_info")
        if not cash_flow_data:
            missing_data.append("cash_flow")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Could not fetch {', '.join(missing_data)} data"
            },
            "agent_name": agent_name,
            "error": "Could not fetch required data (OCF, CapEx, or price)."
        }

    # Extract Market Cap
    market_cap_str = overview_data.get("MarketCapitalization")
    market_cap = None
    if market_cap_str and market_cap_str.lower() not in ["none", "-", ""]:
        try:
            market_cap = float(market_cap_str)
            if market_cap <= 0:
                logger.warning(
                    f"[{agent_name}] Market Cap is zero or negative for {symbol}: {market_cap_str}"
                )
                market_cap = None  # Treat non-positive market cap as invalid for P/FCF
        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse Market Cap for {symbol}: {market_cap_str}"
            )
            market_cap = None

    # Extract FCF components from the latest annual report
    # Assuming cash_flow_data is a dict similar to Alpha Vantage structure for now
    # If it's a DataFrame, this logic needs adjustment.
    fcf = None
    operating_cash_flow = None
    capital_expenditures = None
    raw_ocf_str = None
    raw_capex_str = None

    # Check if cash_flow_data is likely the dict structure from Alpha Vantage
    # or adapt if it's a DataFrame from the provider
    # This part might need refinement based on actual fetch_cash_flow_data output
    if isinstance(cash_flow_data, dict) and cash_flow_data.get("annualReports"):
        latest_annual_report = cash_flow_data["annualReports"][0]
        raw_ocf_str = latest_annual_report.get("operatingCashflow")
        raw_capex_str = latest_annual_report.get("capitalExpenditures")
    # Add handling here if cash_flow_data is a DataFrame
    # elif isinstance(cash_flow_data, pd.DataFrame) and not cash_flow_data.empty:
        # latest_report = cash_flow_data.iloc[0] # Assuming latest is first row
        # raw_ocf_str = latest_report.get("operatingCashflow")
        # raw_capex_str = latest_report.get("capitalExpenditures")
        # logger.warning(f"[{agent_name}] Cash flow data format might be DataFrame - extraction needs verification.")
    else:
         logger.warning(f"[{agent_name}] Unexpected cash flow data format for {symbol}: {type(cash_flow_data)}")


    if raw_ocf_str and raw_ocf_str.lower() not in ["none", "-", ""]:
        try:
            operating_cash_flow = float(raw_ocf_str)
        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse Operating Cash Flow for {symbol}: {raw_ocf_str}"
            )

    # Capex is often reported as negative, but we need its absolute value for FCF calculation
    if raw_capex_str and raw_capex_str.lower() not in ["none", "-", ""]:
        try:
            # Ensure capex is treated as a positive value for subtraction
            capital_expenditures = abs(float(raw_capex_str))
        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse Capital Expenditures for {symbol}: {raw_capex_str}"
            )

    # Calculate FCF if both components are valid numbers
    if (
        operating_cash_flow is not None
        and capital_expenditures is not None
        and not math.isnan(operating_cash_flow)
        and not math.isnan(capital_expenditures)
    ):
        fcf = operating_cash_flow - capital_expenditures
        logger.info(
            f"[{agent_name}] Calculated FCF for {symbol}: {fcf} (OCF: {operating_cash_flow}, CapEx: {capital_expenditures})"
        )
    else:
        logger.warning(
            f"[{agent_name}] Could not calculate FCF for {symbol} due to missing/invalid OCF or CapEx."
        )

    # Calculate P/FCF Ratio
    pfcf_ratio = None
    if (
        market_cap is not None and fcf is not None and fcf > 0
    ):  # FCF must be positive for a meaningful P/FCF
        pfcf_ratio = market_cap / fcf
    elif market_cap is None:
        reason = "Market Cap data missing or invalid."
    elif fcf is None:
        reason = "FCF could not be calculated from cash flow data."
    elif fcf <= 0:
        reason = f"Free Cash Flow is zero or negative ({fcf})."
    else:
        reason = "Unknown issue calculating P/FCF."

    # Check if P/FCF calculation was successful
    if pfcf_ratio is None:
        details = {
            "raw_market_cap": market_cap_str,
            "raw_operating_cash_flow": raw_ocf_str,
            "raw_capital_expenditures": raw_capex_str,
            "calculated_fcf": fcf,
            "reason": reason,
        }
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.1,
            "value": None,
            "details": details,
            "agent_name": agent_name,
            "error": "Could not fetch required data (OCF, CapEx, or price)."
        }

    # Determine Verdict based on P/FCF ratio
    # Lower is generally better. < 15 often considered good, < 25 reasonable.
    if pfcf_ratio < 15:
        verdict = "LOW_PFCF"  # Potentially undervalued
        confidence = 0.7
    elif pfcf_ratio < 25:
        verdict = "MODERATE_PFCF"  # Reasonable range
        confidence = 0.5
    else:  # pfcf_ratio >= 25
        verdict = "HIGH_PFCF"  # Potentially overvalued
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(pfcf_ratio, 2),  # Return the P/FCF ratio
        "details": {
            "pfcf_ratio": round(pfcf_ratio, 2),
            "market_cap": market_cap,
            "free_cash_flow": fcf,
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditures": capital_expenditures,  # Storing the absolute value used
            "data_source": "company_info + cash_flow_data", # Updated source
        },
        "agent_name": agent_name,
        "error": None
    }

    return result
