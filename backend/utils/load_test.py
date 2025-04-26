
import time
import random

def simulate_load(symbols):
    results = []
    for symbol in symbols:
        time.sleep(0.1)  # simulate delay
        results.append({
            "symbol": symbol,
            "status": "OK" if random.random() > 0.05 else "DELAYED"
        })
    return results
