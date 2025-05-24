import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
from unittest.mock import AsyncMock, patch
# Correct import path
from backend.agents.intelligence.factor_score_agent import run as factor_score_run, FactorScoreAgent 

agent_name = "factor_score_agent"

@pytest.mark.asyncio
# Patch the get_market_context method directly on the class prototype
@patch.object(FactorScoreAgent, 'get_market_context', new_callable=AsyncMock)
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) 
async def test_factor_score_agent_strong_bull(
    mock_base_get_redis_client, 
    mock_get_market_context
):
    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    market_regime = "BULL"

    # 1. Mock get_market_context
    mock_get_market_context.return_value = {"regime": market_regime}

    # 2. Mock agent_outputs (provide high confidence, esp. for momentum)
    mock_outputs = {
        # Value Agents (Weight: 0.2 in BULL)
        "pe_ratio_agent": {"confidence": 0.7}, 
        "peg_ratio_agent": {"confidence": 0.8}, # Also used in growth
        "pb_ratio_agent": {"confidence": 0.6},
        # Momentum Agents (Weight: 0.4 in BULL)
        "rsi_agent": {"confidence": 0.9},
        "macd_agent": {"confidence": 0.85},
        "momentum_agent": {"confidence": 0.95},
        # Quality Agents (Weight: 0.2 in BULL)
        "risk_core_agent": {"confidence": 0.75},
        "liquidity_agent": {"confidence": 0.8},
        # Growth Agents (Weight: 0.2 in BULL)
        "earnings_yield_agent": {"confidence": 0.7}, 
        # peg_ratio_agent (0.8) already included
        # Other agents (should be ignored)
        "some_other_agent": {"confidence": 0.5}
    }

    # --- Expected Calculations ---
    # Calculate expected factor scores based on mock_outputs
    expected_value_score = np.mean([0.7, 0.8, 0.6]) # ~0.7
    expected_momentum_score = np.mean([0.9, 0.85, 0.95]) # 0.9
    expected_quality_score = np.mean([0.75, 0.8]) # 0.775
    expected_growth_score = np.mean([0.7, 0.8]) # 0.75

    # Get BULL weights
    weights = {"value": 0.2, "momentum": 0.4, "quality": 0.2, "growth": 0.2}

    # Calculate expected composite score
    expected_factor_score = (
        expected_value_score * weights["value"] + 
        expected_momentum_score * weights["momentum"] + 
        expected_quality_score * weights["quality"] + 
        expected_growth_score * weights["growth"]
    )
    # expected_factor_score = (0.7 * 0.2) + (0.9 * 0.4) + (0.775 * 0.2) + (0.75 * 0.2)
    # expected_factor_score = 0.14 + 0.36 + 0.155 + 0.15 = 0.805

    # Since score > 0.7 => STRONG_FACTORS, confidence = 0.9
    expected_verdict = "STRONG_FACTORS"
    expected_confidence = 0.9

    # --- Run Agent ---
    # The run function creates an instance, so patching the class method works.
    result = await factor_score_run(symbol, agent_outputs=mock_outputs)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_factor_score) # Value is the composite score
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['market_regime'] == market_regime
    assert details['weights'] == weights
    assert 'factor_scores' in details
    f_scores = details['factor_scores']
    assert f_scores['value'] == pytest.approx(expected_value_score)
    assert f_scores['momentum'] == pytest.approx(expected_momentum_score)
    assert f_scores['quality'] == pytest.approx(expected_quality_score)
    assert f_scores['growth'] == pytest.approx(expected_growth_score)

    # --- Verify Mocks ---
    mock_get_market_context.assert_awaited_once_with(symbol)
