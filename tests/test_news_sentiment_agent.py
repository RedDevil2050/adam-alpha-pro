import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.sentiment.news_sentiment_agent import run as ns_run

@pytest.mark.asyncio
async def test_news_sentiment_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_news_headlines', lambda symbol: ['headline'])
    res = await ns_run('ABC', {})
    assert 'sentiment_score' in res
    assert isinstance(res['sentiment_score'], float)