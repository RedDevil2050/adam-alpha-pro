import yfinance as yf

class YahooFinanceProvider:
    @staticmethod
    def fetch_price_data(symbol: str, start_date: str, end_date: str, interval: str = "1d"):
        ticker = yf.Ticker(symbol)
        return ticker.history(start=start_date, end=end_date, interval=interval)

    @staticmethod
    def fetch_quote(symbol: str):
        ticker = yf.Ticker(symbol)
        return ticker.info

    @staticmethod
    def search_symbols(query: str):
        # Yahoo Finance does not provide a direct search API
        return []

    @staticmethod
    def fetch_company_info(symbol: str):
        ticker = yf.Ticker(symbol)
        return ticker.info