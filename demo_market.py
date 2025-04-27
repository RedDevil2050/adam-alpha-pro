import asyncio
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from backend.startup import initialize_system
from backend.orchestrator import run_orchestration
from backend.utils.system_monitor import SystemMonitor

async def run_market_demo():
    logger.info("🚀 Starting Market Demonstration")
    
    # Initialize system
    orchestrator, monitor = await initialize_system()
    if not orchestrator or not monitor:
        logger.error("System initialization failed")
        return False
        
    # Demo symbols
    demo_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]
    
    # Market system status
    logger.info("\n=== System Status ===")
    system_ready = monitor.is_ready()
    logger.info(f"System Ready: {system_ready['ready']}")
    logger.info(f"Components Status: {system_ready['components']}")
    
    # Run sample analysis
    logger.info("\n=== Sample Analysis ===")
    for symbol in demo_symbols:
        try:
            results = await run_orchestration(symbol)
            logger.info(f"\nAnalysis for {symbol}:")
            for agent, output in results.items():
                if "verdict" in output:
                    logger.info(f"{agent}: {output['verdict']}")
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
    
    logger.info("\n=== Market Statistics ===")
    market_stats = await monitor.get_market_metrics()
    logger.info(f"Market Regime: {market_stats.get('regime', 'Unknown')}")
    logger.info(f"System Load: {market_stats.get('system_load', 0)}%")
    
    logger.info("\n✅ Market Demonstration Complete")
    return True

if __name__ == "__main__":
    asyncio.run(run_market_demo())
