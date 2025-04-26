import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from scipy.stats import zscore

class PeerAnalyzer:
    def __init__(self, data_service):
        self.data_service = data_service
        self.peer_cache = {}

    async def get_peer_metrics(self, symbol: str) -> Dict[str, float]:
        peers = await self._identify_peers(symbol)
        metrics = await self._calculate_peer_metrics(peers)
        
        return {
            'pe_percentile': self._calculate_percentile(metrics, 'pe_ratio'),
            'ps_percentile': self._calculate_percentile(metrics, 'price_sales'),
            'ev_ebitda_percentile': self._calculate_percentile(metrics, 'ev_ebitda'),
            'relative_strength': self._calculate_relative_strength(metrics),
        }

    async def _identify_peers(self, symbol: str) -> List[str]:
        if symbol in self.peer_cache:
            return self.peer_cache[symbol]
            
        fundamentals = await self.data_service.get_fundamental_data(symbol)
        sector = fundamentals.get('sector')
        market_cap = fundamentals.get('market_cap')
        
        return await self._filter_comparable_companies(sector, market_cap)

    def _calculate_percentile(self, metrics: pd.DataFrame, column: str) -> float:
        valid_values = metrics[column].dropna()
        return float(zscore(valid_values).mean())
