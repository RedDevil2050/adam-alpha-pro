import requests

class PolygonProvider:
    @staticmethod
    def fetch_price_data(symbol: str, api_key: str):
        url = f"https://api.polygon.io/v1/open-close/{symbol}/2023-01-01?adjusted=true&apiKey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_quote(symbol: str, api_key: str):
        url = f"https://api.polygon.io/v1/last/stocks/{symbol}?apiKey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def search_symbols(query: str, api_key: str):
        url = f"https://api.polygon.io/v3/reference/tickers?search={query}&apiKey={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_company_info(symbol: str, api_key: str):
        url = f"https://api.polygon.io/v1/meta/symbols/{symbol}/company?apiKey={api_key}"
        response = requests.get(url)
        return response.json()