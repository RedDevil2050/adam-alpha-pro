import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
import numpy as np # Import numpy
import datetime # Import datetime
from backend.agents.technical.bollinger_band_agent import run as bb_run

# Test is not async, agent run is synchronous
def test_bollinger_band_agent():
    # Create a list of prices (agent expects List[float])
    # Need at least 20 for the default window
    prices_list = [float(100 + i + np.random.rand()) for i in range(30)]

    # The agent doesn't fetch data, it takes prices directly.
    # No need to mock data_provider if we pass data directly.

    # Call the agent run function with the list of prices
    # Signature: run(prices: List[float], agent_outputs: dict = None)
    res = bb_run(prices_list) # No need for agent_outputs if not used

    # Assertions based on the agent's return dictionary
    assert 'upper_band' in res
    assert 'lower_band' in res
    assert 'mean' in res # Agent returns 'mean', not 'middle_band'
    assert isinstance(res['upper_band'], float)
    assert isinstance(res['lower_band'], float)
    assert isinstance(res['mean'], float)
    assert res['upper_band'] >= res['lower_band']