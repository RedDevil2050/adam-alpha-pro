import json # Import json
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from backend.utils.cache_utils import get_redis_client # Correct import
# from backend.utils.data_provider import fetch_transcript # Temporarily commented out
# Adjust the import below to the correct path where 'tracker' is defined
# For example, if 'utils.py' is in the same directory:
# from . import utils as tracker
# Or, if 'tracker' is a variable or function inside 'utils.py':
# from .utils import tracker
# Assuming tracker is accessible via backend.agents.technical.utils.tracker for now
from backend.agents.technical.utils import tracker
from loguru import logger # Import logger

agent_name = "management_track_record_agent"


async def run(symbol: str) -> dict:
    # Restore original logic now that fetch_transcript stub exists
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client() # Get and await the client
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        try:
            # Attempt to decode JSON if it's stored as a string
            cached_result = json.loads(cached_data)
            return cached_result
        except (json.JSONDecodeError, TypeError):
            # Handle cases where cache might not be JSON (e.g., older format)
            # Or if it's already a dict (though redis usually stores bytes/strings)
            if isinstance(cached_data, dict):
                 return cached_data # Assuming it's the correct structure
            elif isinstance(cached_data, bytes):
                 try:
                     # Try decoding bytes then parsing JSON
                     cached_result = json.loads(cached_data.decode('utf-8'))
                     return cached_result
                 except (json.JSONDecodeError, UnicodeDecodeError):
                     logger.warning(f"Invalid cache format (bytes) for {cache_key}. Re-fetching.")
            else:
                 logger.warning(f"Invalid cache format (unknown type) for {cache_key}. Re-fetching.")


    # Fetch latest earnings transcript using the stubbed/real function
    # Import fetch_transcript here or ensure it's globally available
    from backend.utils.data_provider import fetch_transcript
    text = await fetch_transcript(symbol)
    if not text: # Handle case where transcript fetch fails or returns empty
         result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": 0.0,
            "details": {"reason": "Could not fetch transcript"},
            "agent_name": agent_name,
        }
    else:
        sid = SentimentIntensityAnalyzer()
        # Ensure text is a string before analysis
        if not isinstance(text, str):
             logger.warning(f"Transcript for {symbol} is not a string: {type(text)}. Skipping analysis.")
             result = {
                 "symbol": symbol,
                 "verdict": "ERROR",
                 "confidence": 0.0,
                 "value": 0.0,
                 "details": {"reason": "Invalid transcript format received"},
                 "agent_name": agent_name,
             }
        else:
             score = sid.polarity_scores(text).get("compound", 0.0)

             # Define verdict based on score thresholds (adjust as needed)
             if score > 0.2:
                 verdict = "POSITIVE_CONFIDENCE" # More descriptive verdict
             elif score >= -0.2: # Include neutral range
                 verdict = "NEUTRAL_CONFIDENCE"
             else:
                 verdict = "NEGATIVE_CONFIDENCE"

             result = {
                 "symbol": symbol,
                 "verdict": verdict,
                 "confidence": round(abs(score), 4), # Confidence as magnitude of score
                 "value": round(score, 4), # Keep the raw compound score as value
                 "details": {},
                 "agent_name": agent_name,
             }

    # Cache the result, ensuring it's JSON serializable
    try:
        # Ensure result is serializable before caching
        await redis_client.set(cache_key, json.dumps(result), ex=3600) # Use ex=3600 for 1 hour TTL
    except TypeError as e:
        logger.error(f"Failed to serialize result for caching {cache_key}: {e}")
    except Exception as e:
        logger.error(f"Failed to cache result for {cache_key}: {e}")

    # Assuming tracker.update is synchronous or handled appropriately elsewhere
    try:
        tracker.update("management", agent_name, "implemented")
    except Exception as e:
        logger.error(f"Failed to update tracker for {agent_name}: {e}")

    return result
