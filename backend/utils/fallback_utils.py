import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def fallback_pipeline(data):
    try:
        # Main execution
        return data["result"]
    except KeyError as e:
        logger.error(f"KeyError: Missing key {e} in data: {data}")
        return "FALLBACK_RESULT"
