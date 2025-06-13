"""
Comprehensive Agent Status Checker
Tests all stealth agents and data providers to identify issues
"""

import asyncio
import sys
import os
from loguru import logger

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_all_agents():
    """Test all agents and data providers"""
    logger.info("🔍 COMPREHENSIVE AGENT STATUS CHECK")
    logger.info("=" * 60)
    
    test_symbols = ['RELIANCE', 'TCS', 'INFY']
    results = {}
    
    # Test 1: TrendLyne Agent (we know this works)
    logger.info("\n1️⃣ Testing TrendLyne Agent")
    try:
        from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
        agent = TrendlyneAgent()
        result = await agent.execute('RELIANCE')
        if result and 'signal' in result:
            logger.success(f"✅ TrendLyne Agent: WORKING - {result['signal']}")
            results['trendlyne'] = 'WORKING'
        else:
            logger.error("❌ TrendLyne Agent: FAILED")
            results['trendlyne'] = 'FAILED'
    except Exception as e:
        logger.error(f"❌ TrendLyne Agent: ERROR - {e}")
        results['trendlyne'] = f'ERROR: {e}'
    
    # Test 2: MoneyControl Agent
    logger.info("\n2️⃣ Testing MoneyControl Agent")
    try:
        from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
        agent = MoneyControlAgent()
        result = await agent.execute('RELIANCE')
        if result and 'signal' in result:
            logger.success(f"✅ MoneyControl Agent: WORKING - {result['signal']}")
            results['moneycontrol'] = 'WORKING'
        else:
            logger.warning("⚠️ MoneyControl Agent: NO DATA")
            results['moneycontrol'] = 'NO_DATA'
    except Exception as e:
        logger.error(f"❌ MoneyControl Agent: ERROR - {e}")
        results['moneycontrol'] = f'ERROR: {e}'
    
    # Test 3: Enhanced MoneyControl Agent
    logger.info("\n3️⃣ Testing Enhanced MoneyControl Agent")
    try:
        from backend.agents.stealth.enhanced_moneycontrol_agent import EnhancedMoneyControlAgent
        agent = EnhancedMoneyControlAgent()
        result = await agent.execute('RELIANCE')
        if result and 'signal' in result:
            logger.success(f"✅ Enhanced MoneyControl: WORKING - {result['signal']}")
            results['enhanced_moneycontrol'] = 'WORKING'
        else:
            logger.warning("⚠️ Enhanced MoneyControl: NO DATA")
            results['enhanced_moneycontrol'] = 'NO_DATA'
    except Exception as e:
        logger.error(f"❌ Enhanced MoneyControl: ERROR - {e}")
        results['enhanced_moneycontrol'] = f'ERROR: {e}'
    
    # Test 4: StockEdge Agent
    logger.info("\n4️⃣ Testing StockEdge Agent")
    try:
        from backend.agents.stealth.stockedge_agent import StockEdgeAgent
        agent = StockEdgeAgent()
        result = await agent.execute('RELIANCE')
        if result and 'signal' in result:
            logger.success(f"✅ StockEdge Agent: WORKING - {result['signal']}")
            results['stockedge'] = 'WORKING'
        else:
            logger.warning("⚠️ StockEdge Agent: NO DATA")
            results['stockedge'] = 'NO_DATA'
    except Exception as e:
        logger.error(f"❌ StockEdge Agent: ERROR - {e}")
        results['stockedge'] = f'ERROR: {e}'
    
    # Test 5: Data Providers
    logger.info("\n5️⃣ Testing Data Providers")
    
    # Alpha Vantage
    try:
        from backend.data_providers import DataProviderManager
        manager = DataProviderManager()
        await manager.initialize()
        
        data = await manager.get_stock_data('RELIANCE')
        if data:
            logger.success("✅ Alpha Vantage Provider: WORKING")
            results['alpha_vantage'] = 'WORKING'
        else:
            logger.warning("⚠️ Alpha Vantage Provider: NO DATA")
            results['alpha_vantage'] = 'NO_DATA'
    except Exception as e:
        logger.error(f"❌ Alpha Vantage Provider: ERROR - {e}")
        results['alpha_vantage'] = f'ERROR: {e}'
    
    # Yahoo Finance
    try:
        import yfinance as yf
        ticker = yf.Ticker('RELIANCE.NS')
        info = ticker.info
        if info and 'currentPrice' in info:
            logger.success("✅ Yahoo Finance: WORKING")
            results['yahoo_finance'] = 'WORKING'
        else:
            logger.warning("⚠️ Yahoo Finance: NO DATA")
            results['yahoo_finance'] = 'NO_DATA'
    except Exception as e:
        logger.error(f"❌ Yahoo Finance: ERROR - {e}")
        results['yahoo_finance'] = f'ERROR: {e}'
    
    # Test 6: Emergency Sources
    logger.info("\n6️⃣ Testing Emergency Sources")
    
    emergency_sources = [
        'https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE',
        'https://www.screener.in/company/RELIANCE/',
        'https://www.tickertape.in/stocks/reliance-RELI'
    ]
    
    import httpx
    for i, url in enumerate(emergency_sources):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.success(f"✅ Emergency Source {i+1}: WORKING")
                    results[f'emergency_{i+1}'] = 'WORKING'
                else:
                    logger.warning(f"⚠️ Emergency Source {i+1}: HTTP {response.status_code}")
                    results[f'emergency_{i+1}'] = f'HTTP_{response.status_code}'
        except Exception as e:
            logger.error(f"❌ Emergency Source {i+1}: ERROR - {str(e)[:50]}")
            results[f'emergency_{i+1}'] = 'ERROR'
    
    # Summary Report
    logger.info("\n📊 AGENT STATUS SUMMARY")
    logger.info("=" * 60)
    
    working = [k for k, v in results.items() if v == 'WORKING']
    issues = {k: v for k, v in results.items() if v != 'WORKING'}
    
    logger.info(f"✅ Working Agents/Sources: {len(working)}")
    for agent in working:
        logger.info(f"  • {agent}")
    
    logger.info(f"\n⚠️ Agents with Issues: {len(issues)}")
    for agent, status in issues.items():
        logger.warning(f"  • {agent}: {status}")
    
    # Recommendations
    logger.info("\n💡 RECOMMENDATIONS")
    logger.info("=" * 60)
    
    if len(working) >= 3:
        logger.success("🎉 SYSTEM STATUS: GOOD - Multiple working sources available")
    elif len(working) >= 1:
        logger.warning("⚠️ SYSTEM STATUS: LIMITED - Few working sources, add redundancy")
    else:
        logger.error("❌ SYSTEM STATUS: CRITICAL - No working sources!")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_agents())
