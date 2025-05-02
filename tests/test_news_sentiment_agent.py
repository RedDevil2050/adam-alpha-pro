import pytest
from unittest.mock import AsyncMock, patch # Import patch
from backend.agents.sentiment.news_sentiment_agent import run as ns_run

@pytest.mark.asyncio
@patch('backend.agents.sentiment.news_sentiment_agent.get_redis_client') # Patch redis
@patch('backend.agents.sentiment.news_sentiment_agent.httpx.AsyncClient') # Patch http client
@patch('backend.agents.sentiment.news_sentiment_agent.analyzer') # Patch analyzer where it's USED
async def test_news_sentiment_agent(mock_analyzer, mock_async_client, mock_get_redis):
    # Configure httpx mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    # Simulate NewsAPI response with one good headline
    # Make mock_response.json an AsyncMock that returns the dict when awaited
    mock_response.json = AsyncMock(return_value={
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {"title": "Good news headline", "description": "...", "url": "...", "publishedAt": "..."
            }
        ]
    })
    # Make the client's get method return the mock response
    mock_async_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

    # Configure Redis mock
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Configure sentiment analyzer mock
    # Make polarity_scores return a dict with a positive compound score
    mock_analyzer.polarity_scores.return_value = {'compound': 0.5, 'neu': 0.5, 'pos': 0.5, 'neg': 0.0}

    # Call run with the symbol argument
    res = await ns_run('ABC')

    # Assertions based on the agent's actual return structure
    assert res['symbol'] == 'ABC'
    assert res['verdict'] == 'POSITIVE' # Based on score >= 0.6 (normalized from 0.5 compound)
    assert 'confidence' in res
    # The agent normalizes compound score: (0.5 + 1) / 2 = 0.75
    assert res['confidence'] == pytest.approx(0.75)
    assert 'value' in res # Raw average compound score
    assert res['value'] == pytest.approx(0.5)
    assert 'details' in res
    assert res['details']['headlines_count'] == 1
    assert res.get('error') is None

    # Verify mocks
    mock_analyzer.polarity_scores.assert_called_once_with('Good news headline')
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()
    mock_async_client.return_value.__aenter__.return_value.get.assert_awaited_once()