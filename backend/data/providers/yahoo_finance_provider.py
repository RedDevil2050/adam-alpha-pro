import yfinance as yf
from backend.utils.symbol_normalizer import normalize_indian_symbol

class YahooFinanceProvider:
    @staticmethod
    def fetch_price_data(symbol: str, start_date: str, end_date: str, interval: str = "1d"):
        # Normalize symbol for Yahoo Finance
        normalized_symbol = normalize_indian_symbol(symbol, "yahoo")
        ticker = yf.Ticker(normalized_symbol)
        return ticker.history(start=start_date, end=end_date, interval=interval)

    @staticmethod
    def fetch_quote(symbol: str):
        # Normalize symbol for Yahoo Finance
        normalized_symbol = normalize_indian_symbol(symbol, "yahoo")
        ticker = yf.Ticker(normalized_symbol)
        return ticker.info

    @staticmethod
    def search_symbols(query: str):
        # Yahoo Finance does not provide a direct search API
        return []

    @staticmethod
    def fetch_company_info(symbol: str):
        # Normalize symbol for Yahoo Finance
        normalized_symbol = normalize_indian_symbol(symbol, "yahoo")
        ticker = yf.Ticker(normalized_symbol)
        return ticker.info