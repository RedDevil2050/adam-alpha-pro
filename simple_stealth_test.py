#!/usr/bin/env python3
"""
Simple Stealth Agent Test
========================
A simplified test to validate stealth agents without complex quad-channel processing.
"""

import asyncio
import sys
from pathlib import Path

# Import basic stealth agents
try:
    from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
    from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
    from backend.agents.stealth.stockedge_agent import StockEdgeAgent
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_basic_agent_functionality():
    """Test basic agent functionality without browser automation"""
    print("🚀 SIMPLE STEALTH AGENT TEST")
    print("=" * 40)
    
    # Test symbol
    symbol = "RELIANCE"
    
    # Test agents
    agents = [
        ("MoneyControl", MoneyControlAgent),
        ("TrendLyne", TrendlyneAgent),
        ("StockEdge", StockEdgeAgent)
    ]
    
    results = {}
    
    for agent_name, agent_class in agents:
        print(f"\n📊 Testing {agent_name} Agent...")
        try:
            # Create agent instance
            agent = agent_class()
            
            # Disable browser mode for this test
            if hasattr(agent, 'browser_enabled'):
                agent.browser_enabled = False
            
            # Test basic HTTP functionality
            result = await agent.execute(symbol, {})
            
            if result and not result.get('error'):
                print(f"  ✅ {agent_name}: SUCCESS")
                print(f"     Verdict: {result.get('verdict', 'N/A')}")
                print(f"     Confidence: {result.get('confidence', 0):.2f}")
                results[agent_name] = "SUCCESS"
            else:
                error = result.get('error', 'Unknown error') if result else 'No result'
                print(f"  ⚠️ {agent_name}: PARTIAL - {error}")
                results[agent_name] = f"PARTIAL - {error}"
                
        except Exception as e:
            print(f"  ❌ {agent_name}: FAILED - {e}")
            results[agent_name] = f"FAILED - {e}"
    
    # Summary
    print(f"\n📋 SUMMARY FOR {symbol}")
    print("-" * 30)
    
    success_count = sum(1 for status in results.values() if status == "SUCCESS")
    total_count = len(results)
    
    for agent_name, status in results.items():
        status_emoji = "✅" if status == "SUCCESS" else "⚠️" if "PARTIAL" in status else "❌"
        print(f"{status_emoji} {agent_name}: {status}")
    
    print(f"\n🎯 Overall: {success_count}/{total_count} agents working")
    
    if success_count > 0:
        print("✅ Stealth agents are functional!")
    else:
        print("❌ All agents failed - check configuration")
    
    return results

if __name__ == "__main__":
    try:
        asyncio.run(test_basic_agent_functionality())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
