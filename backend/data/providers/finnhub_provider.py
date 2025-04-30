import requests

class FinnhubProvider:
    @staticmethod
    def fetch_price_data(symbol: str, api_key: str):
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_quote(symbol: str, api_key: str):
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def search_symbols(query: str, api_key: str):
        url = f"https://finnhub.io/api/v1/search?q={query}&token={api_key}"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def fetch_company_info(symbol: str, api_key: str):
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={api_key}"
        response = requests.get(url)
        return response.json()