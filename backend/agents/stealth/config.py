# config.py

class StealthConfig:
    # Existing configuration variables...

    # Updated base URLs for stock data
    TIJORI_BASE_URLS = [
        "https://www.tijori.com/stock",
        "https://tijori.com/stock", 
        "https://www.tijori.com/nse",
        "https://tijori.com/nse",
        "https://www.tijori.com/stocks",  # Legacy
        "https://tijori.com/equity"       # Legacy
    ]
    
    # Circuit breaker settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    CIRCUIT_BREAKER_THRESHOLD = 5
    
    # Existing configuration variables...