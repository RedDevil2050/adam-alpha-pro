#!/usr/bin/env python3
"""
Test all Indian market stealth agents
"""

import asyncio
from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
from backend.agents.stealth.stockedge_agent import StockEdgeAgent
from backend.agents.stealth.tickertape_agent import TickertapeAgent
from backend.agents.stealth.tijori_agent import TijoriAgent
from backend.agents.stealth.tradingview_agent import TradingViewAgent

async def test_all_stealth_agents():
    """Test all available Indian market stealth agents"""
    print('🇮🇳 Testing All Indian Market Stealth Agents')
    print('=' * 60)
    
    agents = [
        ('MoneyControl', MoneyControlAgent()),
        ('Trendlyne', TrendlyneAgent()),
        ('StockEdge', StockEdgeAgent()),
        ('Tickertape', TickertapeAgent()),
        ('Tijori', TijoriAgent()),
        ('TradingView', TradingViewAgent())
    ]
    
    test_symbols = ['RELIANCE', 'TCS', 'INFY']
    results = {}
    
    for symbol in test_symbols:
        print(f'\n📊 Testing symbol: {symbol}')
        print('-' * 40)
        results[symbol] = {}
        
        for agent_name, agent in agents:
            try:
                print(f'  🔍 Testing {agent_name}...', end=' ')
                result = await agent._execute(symbol, {})
                
                verdict = result.get('verdict', 'N/A')
                confidence = result.get('confidence', 0)
                value = result.get('value', 'N/A')
                source = result.get('details', {}).get('source', 'N/A')
                error = result.get('error')
                
                if error:
                    print(f'❌ Error: {error[:50]}...')
                else:
                    print(f'✅ {verdict} (conf: {confidence:.2f}, val: {value})')
                
                results[symbol][agent_name] = {
                    'verdict': verdict,
                    'confidence': confidence,
                    'value': value,
                    'source': source,
                    'success': error is None
                }
                
            except Exception as e:
                print(f'❌ Exception: {str(e)[:50]}...')
                results[symbol][agent_name] = {
                    'success': False,
                    'error': str(e)
                }
    
    # Summary
    print('\n📋 STEALTH AGENTS SUMMARY')
    print('=' * 60)
    
    for symbol in test_symbols:
        print(f'\n📈 {symbol}:')
        for agent_name in [name for name, _ in agents]:
            if agent_name in results[symbol]:
                agent_result = results[symbol][agent_name]
                if agent_result['success']:
                    verdict = agent_result['verdict']
                    confidence = agent_result['confidence']
                    print(f'  ✅ {agent_name:12}: {verdict:6} (confidence: {confidence:.2f})')
                else:
                    print(f'  ❌ {agent_name:12}: FAILED')
    
    # Overall success rate
    total_tests = len(test_symbols) * len(agents)
    successful_tests = sum(
        1 for symbol_results in results.values() 
        for agent_result in symbol_results.values() 
        if agent_result.get('success', False)
    )
    
    success_rate = (successful_tests / total_tests) * 100
    print(f'\n🎯 Overall Success Rate: {successful_tests}/{total_tests} ({success_rate:.1f}%)')
    
    if success_rate >= 70:
        print('🎉 STEALTH AGENTS: WORKING EXCELLENT!')
        print('✅ Indian market data collection is operational!')
    elif success_rate >= 50:
        print('⚠️  STEALTH AGENTS: PARTIALLY WORKING')
        print('🔧 Some agents may need configuration updates')
    else:
        print('❌ STEALTH AGENTS: NEED ATTENTION')
        print('🛠️  Multiple agents require fixes')

if __name__ == "__main__":
    asyncio.run(test_all_stealth_agents())
