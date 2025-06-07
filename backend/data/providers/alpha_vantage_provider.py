import requests
from backend.utils.symbol_normalizer import normalize_indian_symbol

class AlphaVantageProvider:
    @staticmethod
    def fetch_price_data(symbol: str, api_key: str):
        # Normalize symbol for Alpha Vantage
        normalized_symbol = normalize_indian_symbol(symbol, "alpha_vantage")
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={normalized_symbol}&apikey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_quote(symbol: str, api_key: str):
        # Normalize symbol for Alpha Vantage
        normalized_symbol = normalize_indian_symbol(symbol, "alpha_vantage")
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={normalized_symbol}&apikey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def search_symbols(query: str, api_key: str):
        # Note: Search doesn't need normalization as it's for discovering symbols
        url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_company_info(symbol: str, api_key: str):
        # Alpha Vantage does not provide company info directly
        return {}