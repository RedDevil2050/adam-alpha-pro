import yfinance as yf
import pandas as pd


def get_historical_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(symbol + ".NS", start=start, end=end)
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
