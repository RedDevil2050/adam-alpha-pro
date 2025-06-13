#!/usr/bin/env python3
"""
🧠 UNIFIED AGENT INTELLIGENCE TEST SUITE
========================================

Advanced intelligence testing framework for all stealth agents.
Supports AI analysis, advanced metrics, and comprehensive reporting.

Features:
- Multi-agent intelligence testing
- AI analysis capabilities detection
- Advanced scoring and insights
- Market context analysis
- Risk assessment and opportunities
- Sector influence analysis
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
    from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
    from backend.agents.stealth.stockedge_agent import StockEdgeAgent
    from backend.agents.stealth.tickertape_agent import TickertapeAgent
    from backend.agents.stealth.tijori_agent import TijoriAgent
    from backend.agents.stealth.tradingview_agent import TradingViewAgent
    from backend.agents.stealth.zerodha_agent import ZerodhaAgent
    from backend.agents.stealth.screener_agent import ScreenerAgent
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class IntelligenceTestSuite:
    """Unified intelligence testing suite for all agents"""
    
    def __init__(self):
        self.agents = [
            ('MoneyControl', MoneyControlAgent),
            ('TrendLyne', TrendlyneAgent),
            ('StockEdge', StockEdgeAgent),
            ('TickerTape', TickertapeAgent),
            ('Tijori', TijoriAgent),
            ('TradingView', TradingViewAgent),
            ('Zerodha', ZerodhaAgent),
            ('Screener', ScreenerAgent)
        ]
        
        self.test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ITC']
    
    def print_header(self, title: str, char: str = '='):
        """Print formatted header"""
        print(f'\n{title}')
        print(char * len(title))
    
    def print_section(self, title: str):
        """Print section header"""
        print(f'\n📋 {title}')
        print('-' * (len(title) + 4))
    
    async def test_agent_intelligence(self, agent_class, agent_name: str, symbols: List[str] = None) -> Dict:
        """Test intelligence features for any agent"""
        symbols = symbols or self.test_symbols[:3]  # Use first 3 symbols by default
        
        print(f"\n{'='*60}")
        print(f"🧠 Testing {agent_name} Intelligence Features")
        print("="*60)
        
        try:
            agent = agent_class()
        except Exception as e:
            return {'error': f'Failed to initialize agent: {e}', 'agent_name': agent_name}
        
        intelligence_results = {}
        has_ai_features = False
        
        for symbol in symbols:
            print(f"\n🔍 Testing {agent_name} intelligence for {symbol}...")
            try:
                start_time = time.time()
                result = await agent.execute(symbol)
                execution_time = time.time() - start_time
                
                if result:
                    print(f"✅ {symbol} Analysis Complete ({execution_time:.2f}s):")
                    print(f"   📊 Signal: {result.get('verdict', 'N/A')}")
                    print(f"   🎯 Confidence: {result.get('confidence', 0):.2f}")
                    print(f"   💰 Value: {result.get('value', 0):.2f}")
                    
                    # Display AI insights if available
                    details = result.get('details', {})
                    ai_analysis = details.get('ai_analysis', {})
                    
                    if ai_analysis:
                        has_ai_features = True
                        print(f"   🧠 AI Analysis Available:")
                        
                        # Core AI scores
                        scores = {
                            'overall': ai_analysis.get('overall_score', 0),
                            'momentum': ai_analysis.get('momentum_score', 0),
                            'value': ai_analysis.get('value_score', 0),
                            'quality': ai_analysis.get('quality_score', 0),
                            'growth': ai_analysis.get('growth_score', 0),
                            'sentiment': ai_analysis.get('sentiment_score', 0),
                            'risk': ai_analysis.get('risk_score', 0)
                        }
                        
                        for score_name, score_value in scores.items():
                            if score_value > 0:
                                emoji = self._get_score_emoji(score_name)
                                print(f"      {emoji} {score_name.title()} Score: {score_value:.2f}")
                        
                        # Key insights
                        insights = ai_analysis.get('key_insights', [])
                        if insights:
                            print(f"      💡 Key Insights:")
                            for insight in insights[:3]:
                                print(f"         - {insight}")
                        
                        # Risk factors
                        risks = ai_analysis.get('risk_factors', [])
                        if risks:
                            print(f"      ⚠️ Risk Factors:")
                            for risk in risks[:2]:
                                print(f"         - {risk}")
                        
                        # Opportunities
                        opportunities = ai_analysis.get('opportunities', [])
                        if opportunities:
                            print(f"      🌟 Opportunities:")
                            for opp in opportunities[:2]:
                                print(f"         - {opp}")
                    
                    # Technical details
                    intelligence_score = details.get('intelligence_score', 0)
                    if intelligence_score > 0:
                        print(f"   🎯 Intelligence Score: {intelligence_score:.2f}")
                    
                    print(f"   📊 Data Quality: {details.get('data_quality', 'unknown')}")
                    print(f"   🔗 Channels Used: {details.get('channels_used', 'N/A')}")
                    print(f"   📋 Data Completeness: {details.get('data_completeness', 'unknown')}")
                    
                    # Market context
                    market_context = details.get('market_context', {})
                    if market_context:
                        print(f"   🌍 Market Context:")
                        print(f"      - Trend: {market_context.get('market_trend', 'unknown')}")
                        print(f"      - Volatility: {market_context.get('volatility_level', 'unknown')}")
                        print(f"      - Risk Environment: {market_context.get('risk_environment', 'unknown')}")
                    
                    # Sector analysis
                    sector_influence = details.get('sector_influence', {})
                    if sector_influence:
                        print(f"   🏭 Sector Analysis:")
                        print(f"      - Sector: {sector_influence.get('sector', 'unknown')}")
                        print(f"      - Momentum: {sector_influence.get('sector_momentum', 'unknown')}")
                        print(f"      - Outlook: {sector_influence.get('sector_outlook', 'unknown')}")
                    
                    intelligence_results[symbol] = {
                        'verdict': result.get('verdict'),
                        'confidence': result.get('confidence', 0),
                        'value': result.get('value', 0),
                        'ai_analysis': ai_analysis,
                        'intelligence_score': intelligence_score,
                        'data_quality': details.get('data_quality'),
                        'market_context': market_context,
                        'sector_influence': sector_influence,
                        'has_ai_features': bool(ai_analysis),
                        'execution_time': execution_time
                    }
                    
                else:
                    print(f"❌ {symbol}: No result returned")
                    intelligence_results[symbol] = {'error': 'No result', 'has_ai_features': False}
                    
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")
                intelligence_results[symbol] = {'error': str(e), 'has_ai_features': False}
            
            print("-" * 40)
        
        return {
            'agent_name': agent_name,
            'results': intelligence_results,
            'ai_capable': has_ai_features,
            'symbols_tested': len(symbols)
        }
    
    def _get_score_emoji(self, score_name: str) -> str:
        """Get emoji for score type"""
        emoji_map = {
            'overall': '🧠',
            'momentum': '📈', 
            'value': '💎',
            'quality': '🏆',
            'growth': '🚀',
            'sentiment': '😊',
            'risk': '⚠️'
        }
        return emoji_map.get(score_name.lower(), '📊')
    
    async def test_single_agent_intelligence(self, agent_name: str = 'TrendLyne') -> Dict:
        """Test intelligence features for a specific agent"""
        self.print_header(f"🧠 {agent_name.upper()} INTELLIGENCE TEST")
        
        # Find the agent
        agent_class = None
        for name, cls in self.agents:
            if name.lower() == agent_name.lower():
                agent_class = cls
                break
        
        if not agent_class:
            return {'error': f'Agent {agent_name} not found'}
        
        return await self.test_agent_intelligence(agent_class, agent_name, self.test_symbols)
    
    async def test_all_agents_intelligence(self) -> Dict:
        """Test intelligence features across all available agents"""
        self.print_header("🧠 COMPREHENSIVE AGENT INTELLIGENCE TEST")
        
        all_results = {}
        ai_capable_agents = []
        start_time = time.time()
        
        for agent_name, agent_class in self.agents:
            result = await self.test_agent_intelligence(agent_class, agent_name)
            all_results[agent_name] = result
            
            if result.get('ai_capable', False):
                ai_capable_agents.append(agent_name)
        
        total_time = time.time() - start_time
        
        # Summary
        self.print_header("🧠 INTELLIGENCE CAPABILITIES SUMMARY")
        
        print(f"📊 Total Agents Tested: {len(self.agents)}")
        print(f"🧠 AI-Capable Agents: {len(ai_capable_agents)}")
        print(f"⏱️ Total Test Time: {total_time:.1f}s")
        
        if ai_capable_agents:
            print(f"\n✅ Agents with AI Features:")
            for agent in ai_capable_agents:
                agent_data = all_results[agent]
                symbols_with_ai = sum(1 for r in agent_data['results'].values() 
                                    if r.get('has_ai_features', False))
                print(f"   - {agent}: {symbols_with_ai}/{agent_data['symbols_tested']} symbols with AI")
        
        non_ai_agents = [name for name, _ in self.agents if name not in ai_capable_agents]
        if non_ai_agents:
            print(f"\n📋 Standard Agents (No AI Features):")
            for agent in non_ai_agents:
                print(f"   - {agent}")
        
        # Recommendations
        self.print_section("RECOMMENDATIONS")
        
        if len(ai_capable_agents) < len(self.agents) / 2:
            print("🔄 Consider adding AI analysis capabilities to more agents")
            print("   - Implement ai_analysis in agent execute() methods")
            print("   - Add intelligence_score calculations")
            print("   - Include market_context and sector_influence data")
        
        if ai_capable_agents:
            print("🧠 Leverage AI-capable agents for:")
            print("   - Advanced market analysis")
            print("   - Risk assessment and opportunity identification")
            print("   - Intelligent signal generation")
            print("   - Context-aware decision making")
        
        return {
            'total_agents': len(self.agents),
            'ai_capable_count': len(ai_capable_agents),
            'ai_capable_agents': ai_capable_agents,
            'results': all_results,
            'test_duration': total_time
        }

async def main():
    """Main intelligence test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Agent Intelligence Testing Suite')
    parser.add_argument('--mode', choices=['single', 'all', 'trendlyne'], 
                       default='trendlyne', help='Test mode to run')
    parser.add_argument('--agent', default='TrendLyne', 
                       help='Specific agent to test (for single mode)')
    
    args = parser.parse_args()
    
    tester = IntelligenceTestSuite()
    
    try:
        if args.mode == 'single':
            result = await tester.test_single_agent_intelligence(args.agent)
        elif args.mode == 'all':
            result = await tester.test_all_agents_intelligence()
        elif args.mode == 'trendlyne':
            result = await tester.test_single_agent_intelligence('TrendLyne')
        else:
            result = await tester.test_single_agent_intelligence('TrendLyne')
        
        print(f"\n🎉 Intelligence testing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if isinstance(result, dict) and result.get('ai_capable_count', 0) > 0:
            print(f"✅ Found {result['ai_capable_count']} AI-capable agents!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
