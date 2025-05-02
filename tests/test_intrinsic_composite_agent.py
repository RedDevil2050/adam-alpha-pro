import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import AsyncMock, patch # Import patch
from backend.agents.valuation.intrinsic_composite_agent import run as ic_run, agent_name, WEIGHTS, VERDICT_SCORES

@pytest.mark.asyncio
# Patch dependencies in reverse order (decorator dependencies first, then agent runs)
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.valuation.intrinsic_composite_agent.pb_run')
@patch('backend.agents.valuation.intrinsic_composite_agent.pe_run')
@patch('backend.agents.valuation.intrinsic_composite_agent.dcf_run')
async def test_intrinsic_composite_agent_undervalued(
    mock_dcf_run,
    mock_pe_run,
    mock_pb_run,
    mock_get_redis,
    mock_get_tracker
):
    symbol = "TEST_COMP"

    # --- Mock Configuration ---
    # 1. Mock sub-agent results to indicate undervaluation
    mock_dcf_run.return_value = {
        "symbol": symbol, "verdict": "UNDERVALUED", "confidence": 0.8, "value": 120.0, "agent_name": "dcf_agent"
    }
    mock_pe_run.return_value = {
        "symbol": symbol, "verdict": "LOW_PE", "confidence": 0.7, "value": 15.0, "agent_name": "pe_ratio_agent"
    }
    mock_pb_run.return_value = {
        "symbol": symbol, "verdict": "LOW_PB", "confidence": 0.6, "value": 1.2, "agent_name": "pb_ratio_agent"
    }

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Calculation ---
    # dcf_score = VERDICT_SCORES["UNDERVALUED"] * 0.8 * WEIGHTS["dcf"] = 1.0 * 0.8 * 0.4 = 0.32
    # pe_score = VERDICT_SCORES["LOW_PE"] * 0.7 * WEIGHTS["pe"] = 1.0 * 0.7 * 0.3 = 0.21
    # pb_score = VERDICT_SCORES["LOW_PB"] * 0.6 * WEIGHTS["pb"] = 1.0 * 0.6 * 0.3 = 0.18
    # weighted_score_sum = 0.32 + 0.21 + 0.18 = 0.71
    # total_weight = 0.4 + 0.3 + 0.3 = 1.0
    # composite_score = 0.71 / 1.0 = 0.71
    # Since 0.71 > 0.5 => verdict = STRONG_UNDERVALUATION
    # Confidence = min(1.0, 0.71) = 0.71
    expected_composite_score = 0.71
    expected_verdict = "STRONG_UNDERVALUATION"
    expected_confidence = 0.71

    # --- Run Agent ---
    res = await ic_run(symbol)

    # --- Assertions ---
    assert res['symbol'] == symbol
    assert res['agent_name'] == agent_name
    assert res['verdict'] == expected_verdict
    assert res['confidence'] == pytest.approx(expected_confidence, abs=1e-4)
    assert res['value'] == pytest.approx(expected_composite_score, abs=1e-4)
    assert 'details' in res
    assert 'composite_score' in res['details']
    assert res['details']['composite_score'] == pytest.approx(expected_composite_score, abs=1e-4)
    assert 'calculation_breakdown' in res['details']
    assert len(res['details']['calculation_breakdown']) == 3 # All agents succeeded
    assert 'sub_agent_raw_results' in res['details']
    assert 'dcf' in res['details']['sub_agent_raw_results']
    assert 'pe' in res['details']['sub_agent_raw_results']
    assert 'pb' in res['details']['sub_agent_raw_results']
    assert res.get('error') is None

    # --- Verify Mocks ---
    mock_dcf_run.assert_awaited_once_with(symbol, None) # agent_outputs is None by default in run
    mock_pe_run.assert_awaited_once_with(symbol, None)
    mock_pb_run.assert_awaited_once_with(symbol, None)
    mock_get_redis.assert_called_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should be called on success
    mock_get_tracker.assert_called_once()
    # Tracker update is called within the decorator, difficult to assert await directly
    # We rely on mock_get_tracker being called.