
import asyncio
from backend.backtesting.engine import run_backtest

if __name__ == "__main__":
    symbol = "RELIANCE"  # Ensure this exists in data/historical/RELIANCE.csv
    results = asyncio.run(run_backtest(symbol))
    for entry in results[-10:]:
        print(entry)
