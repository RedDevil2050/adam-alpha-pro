#!/usr/bin/env python3
"""
Test script for Indian market stealth agents
"""

import asyncio
from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent

async def test_moneycontrol_agent():
    """Test MoneyControl stealth agent"""
    agent = MoneyControlAgent()
    symbol = 'RELIANCE'
    
    print(f'🔍 Testing MoneyControl agent with {symbol}...')
    
    try:
        result = await agent._execute(symbol, {})
        print(f'✅ Agent executed successfully')
        print(f'   Verdict: {result.get("verdict", "N/A")}')
        print(f'   Confidence: {result.get("confidence", "N/A")}')
        print(f'   Value: {result.get("value", "N/A")}')
        print(f'   Source: {result.get("details", {}).get("source", "N/A")}')
        print(f'   Error: {result.get("error", "None")}')
        return True
    except Exception as e:
        print(f'❌ Agent execution failed: {e}')
        return False

async def main():
    print("🇮🇳 Testing Indian Market Stealth Agents")
    print("=" * 50)
    
    # Test MoneyControl agent
    success = await test_moneycontrol_agent()
    
    if success:
        print("\n🎉 Stealth agent test: SUCCESS")
        print("✅ Indian market data scraping is working!")
    else:
        print("\n❌ Stealth agent test: FAILED")
        print("⚠️  Check network connectivity and agent configuration")

if __name__ == "__main__":
    asyncio.run(main())
