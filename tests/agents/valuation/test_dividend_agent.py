import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.agents.valuation.dividend_agent import run as dividend_agent_run

@pytest.mark.asyncio
async def test_pays_dividend():
    """Test agent correctly identifies stocks that pay dividends"""
    
    # Mock Alpha Vantage response with dividend data
    mock_response = {
        "DividendPerShare": "2.80",
        "ExDividendDate": "2023-08-10",
        "DividendYield": "0.0162"  # 1.62%
    }
    
    # Apply mock
    with patch('backend.agents.valuation.dividend_agent.fetch_alpha_vantage', 
              AsyncMock(return_value=mock_response)):
        
        # Execute agent
        result = await dividend_agent_run("AAPL")
    
    # Assertions
    assert result["symbol"] == "AAPL"
    assert result["verdict"] == "PAYS_DIVIDEND"
    assert result["confidence"] == 0.8
    assert result["value"] == 2.8  # DPS as primary value
    assert result["details"]["dividend_per_share"] == 2.8
    assert result["details"]["ex_dividend_date"] == "2023-08-10"
    assert result["details"]["dividend_yield_percent"] == 1.62
    assert result["details"]["data_source"] == "alpha_vantage_overview"
    assert result["agent_name"] == "dividend_agent"

@pytest.mark.asyncio
async def test_no_dividend_explicit_zero():
    """Test agent correctly identifies stocks that explicitly don't pay dividends (DPS = 0)"""
    
    # Mock Alpha Vantage response with zero dividend
    mock_response = {
        "DividendPerShare": "0",
        "ExDividendDate": "None",
        "DividendYield": "0"
    }
    
    # Apply mock
    with patch('backend.agents.valuation.dividend_agent.fetch_alpha_vantage', 
              AsyncMock(return_value=mock_response)):
        
        # Execute agent
        result = await dividend_agent_run("TSLA")
    
    # Assertions
    assert result["symbol"] == "TSLA"
    assert result["verdict"] == "NO_DIVIDEND"
    assert result["confidence"] == 0.9
    assert result["value"] == 0.0
    assert result["details"]["dividend_per_share"] == 0.0
    assert result["details"]["ex_dividend_date"] is None
    assert result["details"]["dividend_yield_percent"] == 0.0
    assert result["agent_name"] == "dividend_agent"

@pytest.mark.asyncio
async def test_no_dividend_none_string():
    """Test agent correctly handles 'None' as string values"""
    
    # Mock Alpha Vantage response with "None" string values
    mock_response = {
        "DividendPerShare": "None",
        "ExDividendDate": "None",
        "DividendYield": "None"
    }
    
    # Apply mock
    with patch('backend.agents.valuation.dividend_agent.fetch_alpha_vantage', 
              AsyncMock(return_value=mock_response)):
        
        # Execute agent
        result = await dividend_agent_run("AMZN")
    
    # Assertions
    assert result["symbol"] == "AMZN"
    assert result["verdict"] == "NO_DIVIDEND"
    assert result["confidence"] == 0.9
    assert result["value"] == 0.0
    assert result["details"]["dividend_per_share"] is None
    assert result["details"]["ex_dividend_date"] is None
    assert result["details"]["dividend_yield_percent"] is None
    assert result["agent_name"] == "dividend_agent"

@pytest.mark.asyncio
async def test_no_data_api_failure():
    """Test agent handles API failure gracefully"""
    
    # Mock failed API response
    with patch('backend.agents.valuation.dividend_agent.fetch_alpha_vantage', 
              AsyncMock(return_value=None)):
        
        # Execute agent
        result = await dividend_agent_run("INVALID")
    
    # Assertions
    assert result["symbol"] == "INVALID"
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None
    assert "reason" in result["details"]
    assert result["agent_name"] == "dividend_agent"

@pytest.mark.asyncio
async def test_handles_malformed_data():
    """Test agent handles malformed data gracefully"""
    
    # Mock malformed API response
    mock_response = {
        "DividendPerShare": "not-a-number",
        "ExDividendDate": "2023-08-10",
        "DividendYield": "also-not-a-number"
    }
    
    # Apply mock
    with patch('backend.agents.valuation.dividend_agent.fetch_alpha_vantage', 
              AsyncMock(return_value=mock_response)):
        
        # Execute agent
        result = await dividend_agent_run("MALFORMED")
    
    # Assertions
    assert result["symbol"] == "MALFORMED"
    assert result["verdict"] == "NO_DATA"  # Should default to NO_DATA when values can't be parsed
    assert result["value"] is None
    assert result["details"]["dividend_per_share"] is None
    assert result["details"]["ex_dividend_date"] == "2023-08-10"  # Date string should still be parsed
    assert result["details"]["dividend_yield_percent"] is None
    assert result["agent_name"] == "dividend_agent"