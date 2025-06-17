#!/usr/bin/env python3
"""
Agent Health Check Script
========================

This script tests all data collection agents to verify they are working
and collecting company data from designated websites.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from backend.agents.data_collectors.web_scrapers.background_manager import background_manager
from backend.agents.data_collectors.web_scrapers.moneycontrol_agent import MoneyControlAgent
from backend.agents.data_collectors.web_scrapers.trendlyne_agent import TrendlyneAgent
from backend.agents.data_collectors.web_scrapers.stockedge_agent import StockEdgeAgent
from backend.data_providers import data_providers

# Test symbols for verification
TEST_SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'INFY']

async def test_api_providers():
    """Test all API data providers"""
    logger.info("🔍 Testing API Data Providers...")
    
    results = {}
    
    # Test Zerodha
    if 'zerodha' in data_providers.providers:
        try:
            provider = data_providers.providers['zerodha']
            for symbol in TEST_SYMBOLS[:2]:  # Test 2 symbols
                data = await provider.get_live_price(symbol)
                if data and 'price' in data:
                    results[f"zerodha_{symbol}"] = {
                        "status": "✅ Working",
                        "price": data['price'],
                        "data": data
                    }
                    logger.success(f"✅ Zerodha: {symbol} = ₹{data['price']}")
                    break
        except Exception as e:
            results["zerodha"] = {"status": "❌ Failed", "error": str(e)}
            logger.error(f"❌ Zerodha error: {e}")
    
    # Test Alpha Vantage
    if 'alpha_vantage' in data_providers.providers:
        try:
            provider = data_providers.providers['alpha_vantage']
            for symbol in TEST_SYMBOLS[:2]:
                data = await provider.get_quote(symbol)
                if data and 'price' in data:
                    results[f"alpha_vantage_{symbol}"] = {
                        "status": "✅ Working",
                        "price": data['price'],
                        "data": data
                    }
                    logger.success(f"✅ Alpha Vantage: {symbol} = ₹{data['price']}")
                    break
        except Exception as e:
            results["alpha_vantage"] = {"status": "❌ Failed", "error": str(e)}
            logger.error(f"❌ Alpha Vantage error: {e}")
    
    return results

async def test_stealth_agents():
    """Test all stealth agents"""
    logger.info("🕵️ Testing Stealth Agents...")
    
    results = {}
    
    # Initialize agents manually for testing
    agents = {
        'moneycontrol': MoneyControlAgent(),
        'trendlyne': TrendlyneAgent(),
        'stockedge': StockEdgeAgent()
    }
    
    for agent_name, agent in agents.items():
        logger.info(f"🔍 Testing {agent_name} agent...")
        
        for symbol in TEST_SYMBOLS[:2]:  # Test 2 symbols per agent
            try:
                result = await agent.execute(symbol)
                
                if result and result.get('success'):
                    results[f"{agent_name}_{symbol}"] = {
                        "status": "✅ Working",
                        "confidence": result.get('confidence', 0),
                        "price": result.get('price'),
                        "data_quality": result.get('data_quality'),
                        "channels_used": result.get('channels_used', []),
                        "source_websites": result.get('source_websites', [])
                    }
                    logger.success(f"✅ {agent_name}: {symbol} = ₹{result.get('price')} (confidence: {result.get('confidence', 0):.2f})")
                    break
                else:
                    logger.warning(f"⚠️ {agent_name}: {symbol} - no successful data")
                    
            except Exception as e:
                logger.error(f"❌ {agent_name}: {symbol} - {str(e)[:100]}")
                results[f"{agent_name}_error"] = {
                    "status": "❌ Failed",
                    "error": str(e)[:200]
                }
                continue
    
    return results

async def test_background_manager():
    """Test the background manager and its registered agents"""
    logger.info("⚙️ Testing Background Manager...")
    
    try:
        # Check if agents are registered
        registered_agents = list(background_manager.agent_registry.keys())
        logger.info(f"📋 Registered agents: {registered_agents}")
        
        if not registered_agents:
            logger.warning("⚠️ No agents registered in background manager")
            
            # Try to register them manually
            logger.info("🔧 Attempting to register agents manually...")
            
            agents = [
                ("moneycontrol", MoneyControlAgent()),
                ("trendlyne", TrendlyneAgent()),
                ("stockedge", StockEdgeAgent())
            ]
            
            for agent_name, agent_instance in agents:
                background_manager.register_agent(agent_name, agent_instance)
                logger.success(f"✅ Registered {agent_name}")
        
        # Test a registered agent
        if background_manager.agent_registry:
            agent_name = list(background_manager.agent_registry.keys())[0]
            agent = background_manager.agent_registry[agent_name]
            
            logger.info(f"🔍 Testing registered agent: {agent_name}")
            result = await agent.execute('RELIANCE')
            
            if result and result.get('success'):
                logger.success(f"✅ Background manager agent test successful: {agent_name}")
                return {"status": "✅ Working", "agents": registered_agents}
            else:
                logger.warning(f"⚠️ Background manager agent test failed: {agent_name}")
                return {"status": "⚠️ Partial", "agents": registered_agents}
        
    except Exception as e:
        logger.error(f"❌ Background manager error: {e}")
        return {"status": "❌ Failed", "error": str(e)}

async def main():
    """Main test function"""
    logger.info("🚀 Starting comprehensive agent health check...")
    
    # Test API providers
    api_results = await test_api_providers()
    
    # Test stealth agents
    stealth_results = await test_stealth_agents()
    
    # Test background manager
    manager_results = await test_background_manager()
    
    # Summary
    logger.info("📊 HEALTH CHECK SUMMARY")
    logger.info("=" * 50)
    
    working_apis = [k for k, v in api_results.items() if v.get('status', '').startswith('✅')]
    working_stealth = [k for k, v in stealth_results.items() if v.get('status', '').startswith('✅')]
    
    logger.info(f"📈 API Providers Working: {len(working_apis)}/{len(api_results)}")
    for api in working_apis:
        logger.info(f"  ✅ {api}")
    
    logger.info(f"🕵️ Stealth Agents Working: {len(working_stealth)}/{len(stealth_results)}")
    for agent in working_stealth:
        logger.info(f"  ✅ {agent}")
    
    logger.info(f"⚙️ Background Manager: {manager_results.get('status', 'Unknown')}")
    
    # Website coverage analysis
    websites_covered = set()
    for result in stealth_results.values():
        if isinstance(result, dict) and 'source_websites' in result:
            websites_covered.update(result['source_websites'])
    
    logger.info(f"🌐 Websites Being Monitored: {len(websites_covered)}")
    for website in sorted(websites_covered):
        logger.info(f"  📱 {website}")
    
    # Overall health
    total_working = len(working_apis) + len(working_stealth)
    total_possible = len(api_results) + len(stealth_results)
    health_percentage = (total_working / total_possible * 100) if total_possible > 0 else 0
    
    logger.info(f"🎯 Overall System Health: {health_percentage:.1f}%")
    
    if health_percentage >= 70:
        logger.success("✅ System is healthy and collecting data properly!")
    elif health_percentage >= 40:
        logger.warning("⚠️ System is partially working - some agents need attention")
    else:
        logger.error("❌ System needs immediate attention - most agents are failing")

if __name__ == "__main__":
    asyncio.run(main())
