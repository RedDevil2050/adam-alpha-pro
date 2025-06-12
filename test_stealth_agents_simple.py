"""
Simple Stealth Agents Test
==========================

Test stealth agents without complex monkey patching.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def test_single_agent(agent_class, agent_name, symbol, timeout=30):
    """Test a single agent with timeout protection"""
    try:
        agent = agent_class()
        print(f"  ✅ {agent_name} instance created")
        
        start_time = time.time()
        result = await asyncio.wait_for(
            agent.execute(symbol, {}), 
            timeout=timeout
        )
        execution_time = time.time() - start_time
        
        if result.get('error'):
            print(f"  ❌ {agent_name}: FAILED - {result['error'][:60]}...")
            return False
        else:
            verdict = result.get('verdict', 'UNKNOWN')
            confidence = result.get('confidence', 0.0)
            value = result.get('value', 0.0)
            
            print(f"  ✅ {agent_name}: {verdict} (conf: {confidence:.2f}, val: {value:.3f}, {execution_time:.2f}s)")
            
            # Show data quality if available
            if 'details' in result and 'data_quality' in result['details']:
                dq = result['details']['data_quality']
                fusion_conf = dq.get('fusion_confidence', 'N/A')
                channels = dq.get('channels_used', 'N/A')
                print(f"      📊 Quality: fusion={fusion_conf}, channels={channels}")
                
            return True
            
    except asyncio.TimeoutError:
        print(f"  ⏰ {agent_name}: TIMEOUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"  🔥 {agent_name}: EXCEPTION - {str(e)[:60]}...")
        return False

async def main():
    """Simple main test function"""
    
    print("🚀 SIMPLE STEALTH AGENTS TEST")
    print("=" * 40)
    
    # Test symbols
    test_symbols = ['RELIANCE', 'TCS']
    
    # Agent definitions
    agents_to_test = [
        ('MoneyControlAgent', 'backend.agents.stealth.moneycontrol_agent'),
        ('TrendlyneAgent', 'backend.agents.stealth.trendlyne_agent'),
        ('StockEdgeAgent', 'backend.agents.stealth.stockedge_agent'),
        ('TickertapeAgent', 'backend.agents.stealth.tickertape_agent'),
        ('TijoriAgent', 'backend.agents.stealth.tijori_agent'),
        ('TradingViewAgent', 'backend.agents.stealth.tradingview_agent'),
        ('ZerodhaAgent', 'backend.agents.stealth.zerodha_agent')
    ]
    
    total_tests = 0
    successful_tests = 0
    
    for symbol in test_symbols:
        print(f"\n📊 Testing symbol: {symbol}")
        print("-" * 30)
        
        for agent_name, module_path in agents_to_test:
            try:
                # Import agent class
                module = __import__(module_path, fromlist=[agent_name])
                agent_class = getattr(module, agent_name)
                
                # Test the agent
                total_tests += 1
                success = await test_single_agent(agent_class, agent_name, symbol)
                if success:
                    successful_tests += 1
                    
            except ImportError as e:
                print(f"  ❌ Failed to import {agent_name}: {e}")
                total_tests += 1
            except Exception as e:
                print(f"  ❌ Error with {agent_name}: {e}")
                total_tests += 1
    
    # Summary
    print(f"\n📋 SUMMARY")
    print("=" * 30)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 85:
        print("🎉 EXCELLENT! All agents working well!")
    elif success_rate >= 70:
        print("✅ GOOD! Most agents working!")
    elif success_rate >= 50:
        print("⚠️ FAIR! Some issues to address")
    else:
        print("❌ POOR! Major issues detected")

if __name__ == "__main__":
    asyncio.run(main())
