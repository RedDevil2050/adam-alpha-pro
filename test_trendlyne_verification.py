"""
TrendLyne Agent Verification Test
Tests the enhanced TrendLyne agent with live data scraping capabilities
"""

import asyncio
import sys
import os
from loguru import logger

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.agents.stealth.trendlyne_agent import TrendlyneAgent

async def test_trendlyne_agent():
    """Test the enhanced TrendLyne agent"""
    logger.info("🧪 TRENDLYNE AGENT VERIFICATION TEST")
    logger.info("=" * 50)
    
    # Test symbols - mix of high and medium probability
    test_symbols = ['RELIANCE', 'TCS', 'INFY', 'ICICIBANK']
    
    agent = TrendlyneAgent()
    logger.info(f"✅ TrendLyne agent initialized")
    
    results = {}
    
    for symbol in test_symbols:
        logger.info(f"\n🎯 Testing symbol: {symbol}")
        logger.info("-" * 30)
        
        try:
            # Test the agent execution
            result = await agent.execute(symbol)
            
            if result and 'signal' in result:
                logger.success(f"✅ {symbol}: {result['signal']} (conf: {result.get('confidence', 0):.2f})")
                
                # Check for price data in quad-channel metadata
                if 'quad_channel_metadata' in result:
                    channels = result['quad_channel_metadata']['channels_used']
                    logger.info(f"📊 Channels used: {channels}")
                
                # Check factors for price data
                if 'factors' in result and 'price_data' in result['factors']:
                    price = result['factors']['price_data']['current_price']
                    if price > 0:
                        logger.success(f"💰 Live price found: ₹{price}")
                    else:
                        logger.warning(f"⚠️ No price data found")
                
                results[symbol] = {
                    'status': 'success',
                    'signal': result['signal'],
                    'confidence': result.get('confidence', 0),
                    'price': result['factors']['price_data']['current_price'] if 'factors' in result and 'price_data' in result['factors'] else 0
                }
            else:
                logger.error(f"❌ {symbol}: No valid result")
                results[symbol] = {'status': 'failed', 'reason': 'No valid result'}
                
        except Exception as e:
            logger.error(f"💥 {symbol}: Error - {e}")
            results[symbol] = {'status': 'error', 'reason': str(e)}
    
    # Summary
    logger.info(f"\n📋 VERIFICATION SUMMARY")
    logger.info("=" * 50)
    
    successful = [s for s, r in results.items() if r['status'] == 'success']
    failed = [s for s, r in results.items() if r['status'] != 'success']
    
    logger.info(f"✅ Successful: {len(successful)}/{len(test_symbols)}")
    logger.info(f"❌ Failed: {len(failed)}/{len(test_symbols)}")
    
    if successful:
        logger.info(f"\n🎉 Successful symbols:")
        for symbol in successful:
            result = results[symbol]
            price_info = f" - ₹{result['price']}" if result['price'] > 0 else " - No price"
            logger.info(f"  • {symbol}: {result['signal']} (conf: {result['confidence']:.2f}){price_info}")
    
    if failed:
        logger.info(f"\n⚠️ Failed symbols:")
        for symbol in failed:
            result = results[symbol]
            logger.info(f"  • {symbol}: {result['reason']}")
    
    # Overall assessment
    success_rate = len(successful) / len(test_symbols) * 100
    logger.info(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 75:
        logger.success("🎉 EXCELLENT! TrendLyne agent is working well")
    elif success_rate >= 50:
        logger.info("✅ GOOD! TrendLyne agent is functional")
    elif success_rate >= 25:
        logger.warning("⚠️ FAIR! TrendLyne agent needs improvement")
    else:
        logger.error("❌ POOR! TrendLyne agent needs major fixes")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_trendlyne_agent())
