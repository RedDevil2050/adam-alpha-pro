import httpx

async def fetch_price_alpha_vantage(symbol: str) -> float:
    """
    Fetch the latest stock price for the given symbol using Alpha Vantage API.

    Args:
        symbol (str): The stock symbol to fetch the price for.

    Returns:
        float: The latest stock price.
    """
    api_key = "your_alpha_vantage_api_key"  # Replace with your actual API key
    base_url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

    try:
        price = float(data["Global Quote"]["05. price"])
        return price
    except (KeyError, ValueError):
        raise ValueError("Failed to fetch or parse the stock price.")