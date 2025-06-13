#!/usr/bin/env python3
"""
Stealth Agent Health Monitor
Monitor the health and performance of different data sources
"""

import asyncio
import time
from collections import defaultdict
from backend.agents.stealth.stockedge_agent import StockEdgeAgent
from backend.agents.stealth.tijori_agent import TijoriAgent
from backend.agents.stealth.zerodha_agent import ZerodhaAgent
from backend.agents.stealth.tradingview_agent import TradingViewAgent

class SourceHealthMonitor:
    def __init__(self):
        self.source_stats = defaultdict(lambda: {
            'success_count': 0,
            'failure_count': 0,
            'total_requests': 0,
            'avg_response_time': 0,
            'last_success': None,
            'last_failure': None,
            'health_score': 1.0
        })
    
    async def test_agent_health(self, agent_name, agent_class, symbols):
        """Test agent health with multiple symbols"""
        print(f'\n🔍 Testing {agent_name} Health:')
        agent = agent_class()
        
        success_count = 0
        total_time = 0
        
        for symbol in symbols:
            try:
                start_time = time.time()
                result = await agent.execute(symbol, {})
                execution_time = time.time() - start_time
                total_time += execution_time
                
                if result and not result.get('error'):
                    success_count += 1
                    print(f'  ✅ {symbol}: SUCCESS ({execution_time:.2f}s)')
                else:
                    print(f'  ❌ {symbol}: FAILED')
                    
            except Exception as e:
                print(f'  💥 {symbol}: ERROR - {str(e)[:50]}...')
        
        success_rate = (success_count / len(symbols)) * 100
        avg_time = total_time / len(symbols) if symbols else 0
        
        print(f'  📊 Success Rate: {success_rate:.1f}%')
        print(f'  ⏱️  Avg Response Time: {avg_time:.2f}s')
        
        # Health scoring
        if success_rate >= 80:
            health = "🟢 EXCELLENT"
        elif success_rate >= 60:
            health = "🟡 GOOD" 
        elif success_rate >= 40:
            health = "🟠 FAIR"
        else:
            health = "🔴 POOR"
            
        print(f'  💚 Health Status: {health}')
        
        return {
            'agent': agent_name,
            'success_rate': success_rate,
            'avg_response_time': avg_time,
            'health_status': health
        }

async def monitor_stealth_agents():
    """Monitor all stealth agents"""
    print('🩺 STEALTH AGENT HEALTH MONITOR')
    print('=' * 60)
    
    # Test with multiple symbols for better accuracy
    test_symbols = ['RELIANCE', 'TCS', 'INFY']
    
    agents_to_test = [
        ('StockEdge', StockEdgeAgent),
        ('Tijori', TijoriAgent),
        ('TradingView', TradingViewAgent),
        ('Zerodha', ZerodhaAgent)
    ]
    
    monitor = SourceHealthMonitor()
    results = []
    
    for agent_name, agent_class in agents_to_test:
        result = await monitor.test_agent_health(agent_name, agent_class, test_symbols)
        results.append(result)
    
    print(f'\n📈 HEALTH SUMMARY')
    print('=' * 40)
    
    for result in results:
        print(f'{result["agent"]:12} | {result["success_rate"]:5.1f}% | {result["avg_response_time"]:5.2f}s | {result["health_status"]}')
    
    # Overall system health
    overall_success = sum(r['success_rate'] for r in results) / len(results)
    if overall_success >= 70:
        system_health = "🟢 HEALTHY"
    elif overall_success >= 50:
        system_health = "🟡 STABLE"
    else:
        system_health = "🔴 DEGRADED"
    
    print(f'\n🎯 SYSTEM HEALTH: {system_health} ({overall_success:.1f}% overall success)')

if __name__ == "__main__":
    asyncio.run(monitor_stealth_agents())
