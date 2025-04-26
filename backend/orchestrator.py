import functools
import logging
import asyncio
import time

def instrument_agent(name):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logging.info(f"Agent {name} completed in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logging.error(f"Agent {name} failed after {duration:.2f}s: {str(e)}")
                raise
        return wrapper
    return decorator

@instrument_agent("stock_analyzer")
async def analyze_symbol(symbol):
    # Simulate analysis work
    await asyncio.sleep(2)
    return {
        "status": "success",
        "message": f"Analysis complete for {symbol}"
    }

async def run(symbol):
    try:
        result = await analyze_symbol(symbol)
        return {
            "status": "success",
            "message": f"Analysis complete for {symbol}",
            "timestamp": time.time(),
            "data": result
        }
    except Exception as e:
        logging.error(f"Analysis failed for {symbol}: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": time.time()
        }