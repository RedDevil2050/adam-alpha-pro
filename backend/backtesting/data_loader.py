import yfinance as yf
import pandas as pd
from backend.utils.symbol_normalizer import normalize_indian_symbol


def get_historical_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    # Use comprehensive symbol normalization for Yahoo Finance
    normalized_symbol = normalize_indian_symbol(symbol, "yahoo")
    
    df = yf.download(normalized_symbol, start=start, end=end)
    if df.empty:
        return pd.DataFrame()
    df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        },
        inplace=True,
    )
    df.index.name = "date"
    return df.reset_index()
