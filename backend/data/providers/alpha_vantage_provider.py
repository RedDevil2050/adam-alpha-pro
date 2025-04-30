import requests

class AlphaVantageProvider:
    @staticmethod
    def fetch_price_data(symbol: str, api_key: str):
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_quote(symbol: str, api_key: str):
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def search_symbols(query: str, api_key: str):
        url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_company_info(symbol: str, api_key: str):
        # Alpha Vantage does not provide company info directly
        return {}