from backend.utils.data_provider import fetch_price_series
import numpy as np

def run(symbol: str) -> dict:
    try:
        # Fetch historical price series
        price_series = fetch_price_series(symbol, period="1y")

        if price_series is None or len(price_series) < 2:
            return {
                "symbol": symbol,
                "sharpe_ratio": None,
                "status": "NO_DATA",
                "error": "Insufficient data"
            }

        # Calculate daily returns
        returns = np.diff(price_series) / price_series[:-1]

        # Calculate Sharpe Ratio
        mean_return = np.mean(returns)
        std_dev = np.std(returns)
        risk_free_rate = 0.02 / 252  # Assuming 2% annual risk-free rate

        sharpe_ratio = (mean_return - risk_free_rate) / std_dev if std_dev > 0 else None

        return {
            "symbol": symbol,
            "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio is not None else None,
            "status": "CALCULATED",
            "details": {
                "mean_return": round(mean_return, 4),
                "std_dev": round(std_dev, 4),
                "risk_free_rate": risk_free_rate
            }
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "sharpe_ratio": None,
            "status": "ERROR",
            "error": str(e)
        }