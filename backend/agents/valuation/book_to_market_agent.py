import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from backend.utils.data_provider import fetch_price_point, fetch_book_value
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "book_to_market_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    # Fetch data (Core Logic)
    # Use asyncio.gather for concurrent fetching
    price_data_task = fetch_price_point(symbol)
    book_value_task = fetch_book_value(symbol)
    price_data, book_value = await asyncio.gather(price_data_task, book_value_task)

    price = price_data.get("latestPrice") if price_data else None

    # Validate data (Core Logic)
    if price is None or book_value is None or price <= 0:
        # Return NO_DATA format
        details = {
            "book_value_per_share": book_value,
            "latest_price": price,
            "reason": f"Missing or invalid data (Price: {price}, Book Value: {book_value})"
        }
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": details,
            "agent_name": agent_name
        }

    # Calculate Book-to-Market (Core Logic)
    # Ensure book_value is treated as per share if price is per share
    # Assuming fetch_book_value returns book value per share
    btm_ratio = book_value / price

    # Determine Verdict and Confidence (Core Logic)
    # Confidence can be based on how far the ratio is from 1, capped at 1.0
    if btm_ratio > 1.2: # Significantly undervalued
        verdict = "STRONG_BUY"
        confidence = 0.9
    elif btm_ratio > 0.8: # Undervalued
        verdict = "BUY"
        confidence = 0.7
    elif btm_ratio > 0.5: # Fairly valued to slightly overvalued
        verdict = "HOLD"
        confidence = 0.5
    else: # Overvalued
        verdict = "AVOID"
        confidence = 0.3 # Lower confidence as it's considered overvalued

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(btm_ratio, 4), # Book-to-Market ratio as primary value
        "details": {
            "book_value_per_share": round(book_value, 4),
            "latest_price": round(price, 4),
            "btm_ratio": round(btm_ratio, 4)
            },
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result
