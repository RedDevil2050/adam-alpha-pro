from backend.utils.data_provider import fetch_price_alpha_vantage, fetch_price_moneycontrol

async def run(symbol: str, results: dict = None) -> dict:
    try:
        price = await fetch_price_alpha_vantage(symbol)
        if not price or price <= 0:
            price = await fetch_price_moneycontrol(symbol)
        if not price:
            return {'verdict':'avoid','confidence':0.2}
        verdict = 'strong_buy' if price>200 else 'buy' if price>100 else 'hold'
        confidence = round(min(price/200, 1.0), 2)
        return {'verdict': verdict, 'confidence': confidence, 'price': price}
    except Exception as e:
        return {'verdict':'avoid','confidence':0.0,'error':str(e)}
