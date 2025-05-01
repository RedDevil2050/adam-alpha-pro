import pytest
from unittest.mock import AsyncMock
from backend.agents.sentiment.news_sentiment_agent import run as ns_run

@pytest.mark.asyncio
async def test_news_sentiment_agent(monkeypatch):
    # Corrected function name and made mock async
    monkeypatch.setattr('backend.utils.data_provider.fetch_news_sentiment', AsyncMock(return_value=['Good news headline']))
    # Mock the sentiment analysis function
    monkeypatch.setattr('backend.agents.sentiment.news_sentiment_agent.analyze_sentiment_vader', lambda text: {'compound': 0.5}) # Positive sentiment

    # Call run with only the symbol argument
    res = await ns_run('ABC')
    assert 'sentiment_score' in res
    assert res['sentiment_score'] > 0 # Expecting positive score
    assert res['sentiment_label'] == 'POSITIVE'