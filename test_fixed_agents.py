#!/usr/bin/env python3
"""
Quick test for fixed stealth agents
"""
import asyncio
import sys
from loguru import logger

async def test_fixed_agents():
    """Test the fixed stealth agents"""
    print("🔧 TESTING FIXED STEALTH AGENTS")
    print("=" * 50)
    
    # Test symbols
    test_symbols = ["RELIANCE", "TCS"]
    
    # Import agents
    try:
        from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
        from backend.agents.stealth.stockedge_agent import StockEdgeAgent
        from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
        
        agents = [
            (TrendlyneAgent, "TrendLyne"),
            (StockEdgeAgent, "StockEdge"), 
            (MoneyControlAgent, "MoneyControl")
        ]
        
        for symbol in test_symbols:
            print(f"\n📊 Testing with symbol: {symbol}")
            print("-" * 30)
            
            for agent_class, agent_name in agents:
                try:
                    print(f"🔍 Testing {agent_name}...")
                    agent = agent_class()
                    
                    # Disable browser automation for testing
                    if hasattr(agent, 'browser_enabled'):
                        agent.browser_enabled = False
                    
                    # Quick test - just check if methods exist and can be called
                    if hasattr(agent, '_parse_trendlyne_page'):
                        print(f"✅ {agent_name}: _parse_trendlyne_page method exists")
                    
                    if hasattr(agent, '_extract_price_fallback'):
                        print(f"✅ {agent_name}: _extract_price_fallback method exists")
                    
                    if hasattr(agent, '_try_working_fallback_apis'):
                        print(f"✅ {agent_name}: _try_working_fallback_apis method exists")
                    
                    print(f"✅ {agent_name}: Agent instantiated successfully")
                    
                except Exception as e:
                    print(f"❌ {agent_name}: Error - {e}")
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    print(f"\n🎉 Fixed agent validation completed!")
    return True

if __name__ == "__main__":
    asyncio.run(test_fixed_agents())
