import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import asyncio # Import asyncio
from backend.utils.data_provider import fetch_price_point, fetch_book_value
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator
from backend.config.settings import get_settings # Import get_settings

agent_name = "book_to_market_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Added agent_outputs default
    """
    Calculates the Book-to-Market (B/M) ratio for a given stock symbol and assesses its valuation.

    Purpose:
        Determines the B/M ratio, which compares a company's book value (accounting value) to its market value.
        It's often used by value investors; a higher ratio (book value > market value) can suggest undervaluation.

    Metrics Calculated:
        - Book-to-Market Ratio (Book Value per Share / Market Price per Share)

    Logic:
        1. Fetches the latest stock price using `fetch_price_point`.
        2. Fetches the book value per share using `fetch_book_value`.
        3. Validates that both price and book value are available and positive.
        4. Calculates the B/M ratio.
        5. Compares the B/M ratio against configurable thresholds (THRESHOLD_UNDERVALUED_BTM, THRESHOLD_OVERVALUED_BTM):
            - If B/M <= 0: Verdict is 'NEGATIVE_OR_ZERO_BV'.
            - If B/M > THRESHOLD_UNDERVALUED_BTM: Verdict is 'UNDERVALUED'.
            - If THRESHOLD_OVERVALUED_BTM < B/M <= THRESHOLD_UNDERVALUED_BTM: Verdict is 'FAIRLY_VALUED'.
            - If 0 < B/M <= THRESHOLD_OVERVALUED_BTM: Verdict is 'OVERVALUED'.
        6. Sets a fixed confidence score based on the verdict category.

    Dependencies:
        - Requires latest stock price (`fetch_price_point`).
        - Requires book value per share (`fetch_book_value`).

    Configuration Used (Requires manual addition to settings.py):
        - `settings.agent_settings.book_to_market.THRESHOLD_UNDERVALUED_BTM`: Lower bound for 'UNDERVALUED'.
        - `settings.agent_settings.book_to_market.THRESHOLD_OVERVALUED_BTM`: Lower bound for 'FAIRLY_VALUED'.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED', 'FAIRLY_VALUED', 'OVERVALUED', 'NEGATIVE_OR_ZERO_BV', or 'NO_DATA'.
        - confidence (float): A fixed score based on the verdict category (0.0 to 1.0).
        - value (float | None): The calculated B/M ratio, or None if not available/applicable.
        - details (dict): Contains book value, price, B/M ratio, and configured thresholds.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    # Fetch settings
    settings = get_settings()
    btm_settings = settings.agent_settings.book_to_market

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

    # Determine Verdict and Confidence using standardized verdicts
    if btm_ratio <= 0:
        verdict = "NEGATIVE_OR_ZERO_BV" # Specific case if book value is negative
        confidence = 0.7
    elif btm_ratio > btm_settings.THRESHOLD_UNDERVALUED_BTM: # Use setting
        verdict = "UNDERVALUED"
        confidence = 0.7 # Higher confidence for stronger signal
    elif btm_ratio > btm_settings.THRESHOLD_OVERVALUED_BTM: # Use setting
        verdict = "FAIRLY_VALUED"
        confidence = 0.5
    else: # Low BTM -> Overvalued
        verdict = "OVERVALUED"
        confidence = 0.4 # Lower confidence as it's considered overvalued

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(btm_ratio, 4), # Book-to-Market ratio as primary value
        "details": {
            "book_value_per_share": round(book_value, 4),
            "latest_price": round(price, 4),
            "btm_ratio": round(btm_ratio, 4),
            # Add thresholds from settings to details
            "threshold_undervalued": btm_settings.THRESHOLD_UNDERVALUED_BTM,
            "threshold_overvalued": btm_settings.THRESHOLD_OVERVALUED_BTM
            },
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result
