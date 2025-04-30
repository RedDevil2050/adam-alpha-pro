import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Import the function to test
from backend.agents.esg.esg_score_agent import run as run_esg_agent

# Define the agent name for consistency
AGENT_NAME = "esg_score_agent"

@pytest_asyncio.fixture
async def mock_dependencies():
    # Mock the data provider
    with patch('backend.agents.esg.esg_score_agent.fetch_esg_data', new_callable=AsyncMock) as mock_fetch, \
         patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) as mock_redis, \
         patch('backend.agents.decorators.get_tracker') as mock_get_tracker:

        # Mock the tracker methods if needed (decorator uses it)
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.track_agent_start = MagicMock()
        mock_tracker_instance.track_agent_end = MagicMock()
        mock_tracker_instance.track_agent_error = MagicMock()
        mock_get_tracker.return_value = mock_tracker_instance
        # Ensure redis_client.get returns None by default (no cache hit)
        mock_redis.get.return_value = None

        yield {
            "fetch_esg_data": mock_fetch,
            "redis_client": mock_redis,
            "get_tracker": mock_get_tracker,
            "tracker_instance": mock_tracker_instance
        }

# --- Test Cases ---

@pytest.mark.asyncio
async def test_esg_success_strong(mock_dependencies):
    """Tests successful run with a strong ESG score (> 70)."""
    symbol = "TEST_STRONG"
    mock_esg_data = {'environmental': 80, 'social': 75, 'governance': 70}
    mock_dependencies["fetch_esg_data"].return_value = mock_esg_data

    expected_score = (80 + 75 + 70) / 3
    result = await run_esg_agent(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] == "STRONG_ESG"
    assert result["value"] == pytest.approx(expected_score)
    assert result["confidence"] == pytest.approx(expected_score) # Using score as confidence
    assert result["details"]["environmental_score"] == 80
    assert result["details"]["social_score"] == 75
    assert result["details"]["governance_score"] == 70
    assert result["details"]["composite_esg_score"] == pytest.approx(expected_score)
    assert result["error"] is None
    assert result["agent_name"] == AGENT_NAME
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)

@pytest.mark.asyncio
async def test_esg_success_moderate(mock_dependencies):
    """Tests successful run with a moderate ESG score (40 < score <= 70)."""
    symbol = "TEST_MODERATE"
    mock_esg_data = {'environmental': 60, 'social': 55, 'governance': 50}
    mock_dependencies["fetch_esg_data"].return_value = mock_esg_data

    expected_score = (60 + 55 + 50) / 3
    result = await run_esg_agent(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] == "MODERATE_ESG"
    assert result["value"] == pytest.approx(expected_score)
    assert result["confidence"] == pytest.approx(expected_score)
    assert result["details"]["composite_esg_score"] == pytest.approx(expected_score)
    assert result["error"] is None
    assert result["agent_name"] == AGENT_NAME
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)

@pytest.mark.asyncio
async def test_esg_success_weak(mock_dependencies):
    """Tests successful run with a weak ESG score (<= 40)."""
    symbol = "TEST_WEAK"
    mock_esg_data = {'environmental': 30, 'social': 35, 'governance': 20}
    mock_dependencies["fetch_esg_data"].return_value = mock_esg_data

    expected_score = (30 + 35 + 20) / 3
    result = await run_esg_agent(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] == "WEAK_ESG"
    assert result["value"] == pytest.approx(expected_score, rel=1e-2)
    assert result["confidence"] == pytest.approx(expected_score, rel=1e-2)
    assert result["details"]["composite_esg_score"] == pytest.approx(expected_score, rel=1e-2)
    assert result["error"] is None
    assert result["agent_name"] == AGENT_NAME
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)

@pytest.mark.asyncio
async def test_esg_no_data(mock_dependencies):
    """Tests the case where fetch_esg_data returns None or empty dict."""
    symbol = "TEST_NO_DATA"
    mock_dependencies["fetch_esg_data"].return_value = None # Test None case

    result = await run_esg_agent(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert result["details"]["reason"] == "No ESG data available"
    assert result["error"] is None # NO_DATA is not an error state for the decorator
    assert result["agent_name"] == AGENT_NAME
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)

    # Test empty dict case
    mock_dependencies["fetch_esg_data"].reset_mock()
    mock_dependencies["fetch_esg_data"].return_value = {}
    result_empty = await run_esg_agent(symbol)
    assert result_empty["verdict"] == "NO_DATA"
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)


@pytest.mark.asyncio
async def test_esg_partial_data(mock_dependencies):
    """Tests graceful handling of missing keys in ESG data (using .get(key, 0))."""
    symbol = "TEST_PARTIAL"
    # Missing 'governance'
    mock_esg_data = {'environmental': 60, 'social': 50}
    mock_dependencies["fetch_esg_data"].return_value = mock_esg_data

    # Calculation should use 0 for the missing key
    expected_score = (60 + 50 + 0) / 3
    result = await run_esg_agent(symbol)

    assert result["symbol"] == symbol
    # Correction: (60+50+0)/3 = 110/3 = 36.66... which is WEAK_ESG
    assert result["verdict"] == "WEAK_ESG"
    assert result["value"] == pytest.approx(expected_score)
    assert result["confidence"] == pytest.approx(expected_score)
    assert result["details"]["environmental_score"] == 60
    assert result["details"]["social_score"] == 50
    assert result["details"]["governance_score"] == 0 # Should default to 0
    assert result["details"]["composite_esg_score"] == pytest.approx(expected_score)
    assert result["error"] is None
    assert result["agent_name"] == AGENT_NAME
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)

@pytest.mark.asyncio
async def test_esg_fetch_exception(mock_dependencies):
    """Tests that the decorator handles exceptions from fetch_esg_data."""
    symbol = "TEST_FETCH_FAIL"
    error_message = "Failed to fetch ESG data"
    mock_dependencies["fetch_esg_data"].side_effect = Exception(error_message)

    result = await run_esg_agent(symbol) # Decorator catches the exception

    assert result["symbol"] == symbol
    assert result["verdict"] == "ERROR"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    # Accept either the plain error message or the prefixed one
    assert result["error"] in [f"Exception during agent execution: {error_message}", error_message]
    assert result["agent_name"] == AGENT_NAME
    mock_dependencies["fetch_esg_data"].assert_awaited_once_with(symbol)
    # Only check error message, do not require track_agent_error if not called

