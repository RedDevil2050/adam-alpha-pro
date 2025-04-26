
import re

def validate_stock_data(data: dict) -> bool:
    # Sample schema fields check
    required = ["symbol", "price", "eps", "pe"]
    for field in required:
        if field not in data or not isinstance(data[field], (int, float, str)):
            return False
    return True

def preprocess_input(data: dict) -> dict:
    # Normalize and clean
    data['symbol'] = str(data.get('symbol', '')).upper().strip()
    data['price'] = float(data.get('price', 0))
    data['eps'] = float(data.get('eps', 0))
    data['pe'] = float(data.get('pe', 0))
    return data

def run_etl(raw_data: dict) -> dict:
    cleaned = preprocess_input(raw_data)
    if not validate_stock_data(cleaned):
        raise ValueError("Invalid input data schema")
    return cleaned
