import sys, os, asyncio, time, json, argparse, logging
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

# Optional psutil import
try:
    import psutil
    MEMORY_TRACKING = True
except ImportError:
    MEMORY_TRACKING = False
    print("Note: Install 'psutil' for memory tracking: pip install psutil")

sys.path.append(os.path.abspath("."))

from backend.orchestrator import run

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_analysis.log'),
        logging.StreamHandler()
    ]
)

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='Batch analysis of stock symbols',
    epilog='Example: python batch_test_gemini.py --symbols TCS INFY --output results.json'
)
parser.add_argument('--symbols', nargs='+', help='List of symbols to analyze',
                   default=["TCS", "INFY", "RELIANCE", "ITC", "HDFCBANK"])
parser.add_argument('--output', help='Output file path',
                   default='analysis_results.json')
parser.add_argument('--chunk-size', type=int, default=2,
                   help='Number of concurrent requests')
parser.add_argument('--max-retries', type=int, default=3,
                   help='Maximum number of retries per symbol')

args = parser.parse_args()
if not args.symbols:
    parser.error("At least one symbol must be provided")

def get_memory_usage():
    if MEMORY_TRACKING:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # in MB
    return 0  # Return 0 if psutil is not available

async def process_symbol(symbol, semaphore, pbar):
    async with semaphore:
        start_mem = get_memory_usage() if MEMORY_TRACKING else None
        try:
            for attempt in range(args.max_retries):
                try:
                    start = time.time()
                    result = await run(symbol)
                    duration = time.time() - start
                    pbar.update(1)
                    return {
                        "symbol": symbol,
                        "success": True,
                        "duration": f"{duration:.2f}s",
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                        **({"memory_used": f"{get_memory_usage() - start_mem:.2f}MB"} if MEMORY_TRACKING else {})
                    }
                except Exception as e:
                    if attempt == args.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
            
        except Exception as e:
            logging.error(f"Error processing {symbol}: {str(e)}")
            pbar.update(1)
            return {
                "symbol": symbol,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                **({"memory_used": f"{get_memory_usage() - start_mem:.2f}MB"} if MEMORY_TRACKING else {})
            }

async def main():
    print(f"Starting batch analysis at {datetime.now()}")
    print(f"Processing {len(args.symbols)} symbols: {', '.join(args.symbols)}\n")
    
    start_time = time.time()  # Define start_time here
    semaphore = asyncio.Semaphore(args.chunk_size)
    total_symbols = len(args.symbols)
    
    with tqdm(total=total_symbols, desc="Analyzing") as pbar:
        results = await asyncio.gather(*[
            process_symbol(sym, semaphore, pbar) 
            for sym in args.symbols
        ])
    
    # Generate performance metrics
    success_count = sum(1 for r in results if r["success"])
    total_duration = time.time() - start_time
    performance_metrics = {
        "total_symbols": total_symbols,
        "successful": success_count,
        "failed": total_symbols - success_count,
        "success_rate": f"{(success_count/total_symbols)*100:.1f}%",
        "avg_time_per_symbol": f"{total_duration/total_symbols:.2f}s",
        "total_duration": f"{total_duration:.2f}s",
        **({"peak_memory": f"{get_memory_usage():.2f}MB"} if MEMORY_TRACKING else {})
    }
    
    # Save results with metrics
    output_data = {
        "analysis_time": datetime.now().isoformat(),
        "performance_metrics": performance_metrics,
        "results": results
    }
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print("\nResults Summary:")
    print("-" * 50)
    
    for r in results:
        sym = r["symbol"]
        if r["success"]:
            print(f"✓ {sym} (took {r['duration']})")
            print(f"  Result: {r['result']}\n")
        else:
            print(f"✗ {sym} - Failed: {r['error']}\n")
    
    logging.info(f"Results saved to {output_path}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)
