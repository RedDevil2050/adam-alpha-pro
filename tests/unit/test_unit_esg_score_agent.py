import pytest
from unittest.mock import patch, MagicMock
# Import the run function instead of the non-existent class
from backend.agents.esg.esg_score_agent import run as run_esg_agent

@pytest.mark.asyncio
@patch('backend.agents.esg.esg_score_agent.get_settings') # Mock settings
@patch('backend.agents.esg.esg_score_agent.fetch_esg_data') # Mock data fetching
async def test_esg_score_agent(mock_fetch_esg_data, mock_get_settings):
    # Configure mock settings
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.esg_score.THRESHOLD_STRONG_ESG = 70.0
    mock_settings_instance.agent_settings.esg_score.THRESHOLD_MODERATE_ESG = 40.0
    mock_get_settings.return_value = mock_settings_instance

    # Configure mock data provider to return sample data
    mock_fetch_esg_data.return_value = {
        "environmental": 80,
        "social": 75,
        "governance": 90
    }

    symbol = "AAPL"
    # Call the run function directly
    result = await run_esg_agent(symbol)

    # Assertions based on the expected output of the run function
    assert result["symbol"] == symbol
    assert result["verdict"] == "STRONG_ESG" # Based on mock data and thresholds
    assert result["confidence"] == 81.67 # (80 + 75 + 90) / 3
    assert result["value"] == 81.67
    assert result["error"] is None
    assert result["agent_name"] == "esg_score_agent"
    mock_fetch_esg_data.assert_called_once_with(symbol) # Corrected assertion

@pytest.mark.asyncio
@patch('backend.agents.esg.esg_score_agent.get_settings')
@patch('backend.agents.esg.esg_score_agent.fetch_esg_data')
async def test_esg_score_agent_no_data(mock_fetch_esg_data, mock_get_settings):
    # Configure mock settings (needed even if data fetch fails)
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.esg_score.THRESHOLD_STRONG_ESG = 70.0
    mock_settings_instance.agent_settings.esg_score.THRESHOLD_MODERATE_ESG = 40.0
    mock_get_settings.return_value = mock_settings_instance

    # Configure mock data provider to return None (no data)
    mock_fetch_esg_data.return_value = None

    symbol = "NODATA"
    result = await run_esg_agent(symbol)

    # Assertions for NO_DATA case
    assert result["symbol"] == symbol
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None
    assert result["error"] is None # NO_DATA is not an error state for the agent logic
    assert "No ESG data available" in result["details"]["reason"]
    assert result["agent_name"] == "esg_score_agent"
    mock_fetch_esg_data.assert_called_once_with(symbol) # Corrected assertion