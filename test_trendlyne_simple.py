"""
Simple TrendLyne Agent Test
"""

import asyncio
import sys
import os
from loguru import logger

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_simple_trendlyne():
    """Simple test for TrendLyne agent"""
    try:
        from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
        
        logger.info("🧪 SIMPLE TRENDLYNE TEST")
        logger.info("=" * 30)
        
        agent = TrendlyneAgent()
        logger.info("✅ TrendLyne agent created successfully")
        
        # Test with a simple symbol
        symbol = 'RELIANCE'
        logger.info(f"🎯 Testing {symbol}")
        
        try:
            result = await agent.execute(symbol)
            
            if result and 'signal' in result:
                logger.success(f"✅ SUCCESS: {symbol} -> {result['signal']}")
                logger.info(f"📊 Confidence: {result.get('confidence', 0):.2f}")
                
                if 'factors' in result and 'price_data' in result['factors']:
                    price = result['factors']['price_data']['current_price']
                    if price > 0:
                        logger.success(f"💰 Price found: ₹{price}")
                    else:
                        logger.warning("⚠️ No price data")
                else:
                    logger.warning("⚠️ No price factors")
                
                return True
            else:
                logger.error("❌ No valid result returned")
                return False
                
        except Exception as e:
            logger.error(f"💥 Error during execution: {e}")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_trendlyne())
    if success:
        print("\n🎉 TrendLyne agent is working!")
    else:
        print("\n❌ TrendLyne agent needs fixing")
