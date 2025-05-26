import pytest
from unittest.mock import AsyncMock, patch, MagicMock # Added MagicMock
from backend.agents.sentiment.news_sentiment_agent import run as ns_run
from backend.config.settings import Settings, AgentSettings # Import Settings, AgentSettings

# Create a mock settings object to be used in the patch
mock_settings_for_news_agent = MagicMock(spec=Settings)
mock_settings_for_news_agent.news_api_key = "test_key_mocked"
# If the agent used other settings, they would be configured here, for example:
# mock_settings_for_news_agent.some_other_setting = "value"
# mock_settings_for_news_agent.agent_settings = MagicMock(spec=AgentSettings)
# mock_settings_for_news_agent.agent_settings.agent_cache_ttl_seconds = 3600


@pytest.mark.asyncio
# Patch the settings object in the news_sentiment_agent module with our mock instance
# The mock objects are passed to the test function in order from the bottom decorator upwards.
@patch('backend.agents.sentiment.news_sentiment_agent.analyzer')
@patch('backend.agents.sentiment.news_sentiment_agent.httpx.AsyncClient')
@patch('backend.agents.sentiment.news_sentiment_agent.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.sentiment.news_sentiment_agent.settings', mock_settings_for_news_agent)
async def test_news_sentiment_agent(mock_settings_patched_ref, mock_get_redis_client, mock_async_httpx_client, mock_analyzer): # Args reordered to match decorator order
    # Configure httpx mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {"title": "Good news headline", "description": "...", "url": "...", "publishedAt": "..."}
        ]
    })

    # Configure the client instance mock that httpx.AsyncClient() will return
    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    
    mock_client_instance.__aenter__.return_value = mock_client_instance 
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    # Assign the configured client instance to the return_value of the httpx.AsyncClient mock
    mock_async_httpx_client.return_value = mock_client_instance

    # Configure Redis mock
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    # Assign the configured redis instance to the return_value of the get_redis_client mock
    mock_get_redis_client.return_value = mock_redis_instance

    # Configure sentiment analyzer mock
    mock_analyzer.polarity_scores.return_value = {'compound': 0.5, 'neu': 0.5, 'pos': 0.5, 'neg': 0.0}

    # Call run with the symbol argument
    res = await ns_run('ABC')

    # Assertions
    assert res['symbol'] == 'ABC'
    # The agent normalizes compound score: (0.5 + 1) / 2 = 0.75.
    # Verdict is POSITIVE if normalized score >= 0.6
    assert res['verdict'] == 'POSITIVE' 
    assert 'confidence' in res
    assert res['confidence'] == pytest.approx(0.75)
    assert 'value' in res 
    assert res['value'] == pytest.approx(0.5)
    assert 'details' in res
    assert res['details']['headlines_count'] == 1
    assert res.get('error') is None

    # Verify mocks
    mock_analyzer.polarity_scores.assert_called_once_with('Good news headline')
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()
    mock_async_httpx_client.assert_called_once_with(timeout=10)
    mock_client_instance.get.assert_awaited_once()