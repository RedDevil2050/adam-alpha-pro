from gensim import corpora, models
from backend.utils.cache_utils import get_redis_client
from backend.utils.progress_tracker import ProgressTracker

agent_name = "nlp_topic_agent"

# Define or initialize the tracker instance
tracker = ProgressTracker(filepath="backend/utils/progress.json")


async def run(texts: list) -> dict:
    redis_client = get_redis_client()
    cache_key = f"{agent_name}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    tokens = [t.split() for t in texts]
    dictionary = corpora.Dictionary(tokens)
    corpus = [dictionary.doc2bow(tok) for tok in tokens]
    lda = models.LdaModel(corpus, num_topics=3, id2word=dictionary)
    topics = lda.print_topics()

    result = {
        "symbol": None,
        "verdict": "TOPICS_EXTRACTED",
        "confidence": 1.0,
        "value": topics,
        "details": {},
        "score": 1.0,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("nlp", agent_name, "implemented")
    return result
