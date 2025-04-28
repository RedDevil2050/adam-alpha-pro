from typing import Dict

def run(symbol: str) -> Dict[str, float]:
    """Simulate calculating drawdown for a given symbol."""
    return {"symbol": symbol, "max_drawdown": -15.0, "status": "calculated"}