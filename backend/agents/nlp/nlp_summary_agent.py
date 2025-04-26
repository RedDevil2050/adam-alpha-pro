from transformers import pipeline
from backend.utils.cache_utils import redis_client
from backend.agents.nlp.utils import tracker

agent_name = "nlp_summary_agent"

async def run(text: str) -> dict:
    cache_key = f"{agent_name}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    summarizer = pipeline("summarization")
    summary = summarizer(text, max_length=80)[0]["summary_text"]

    result = {"symbol": None, "verdict": "SUMMARIZED", "confidence":1.0,
              "value":summary, "details":{}, "score":1.0, "agent_name":agent_name}

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("nlp", agent_name, "implemented")
    return result
