from transformers import pipeline
from backend.utils.cache_utils import get_redis_client

# Try importing tracker, fallback to a dummy tracker if not found
import logging

import importlib

try:
    nlp_utils = importlib.import_module("backend.agents.nlp.utils")
    tracker = getattr(nlp_utils, "tracker", None)
    if tracker is None:
        raise ImportError("tracker not found in backend.agents.nlp.utils")
except ImportError:
    logging.warning("Could not import 'tracker' from 'backend.agents.nlp.utils'. Using DummyTracker instead.")
    class DummyTracker:
        def update(self, *args, **kwargs):
            pass
    tracker = DummyTracker()

# Initialize redis client
redis_client = get_redis_client()

agent_name = "nlp_summary_agent"


async def run(text: str) -> dict:
    cache_key = f"{agent_name}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    summarizer = pipeline("summarization")
    summary = summarizer(text, max_length=80)[0]["summary_text"]

    result = {
        "symbol": None,
        "verdict": "SUMMARIZED",
        "confidence": 1.0,
        "value": summary,
        "details": {},
        "score": 1.0,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("nlp", agent_name, "implemented")
    return result
