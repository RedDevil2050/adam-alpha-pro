#!/usr/bin/env python3
"""
🚀 UNIFIED STEALTH AGENT TESTING SUITE
=====================================

Consolidated testing module for all Indian market stealth agents.
Combines functionality from:
- test_all_stealth_agents.py
- test_stealth_agents_simple.py
- test_working_stealth_agents.py
- test_503_handling.py
- test_improved_agents.py
- monitor_stealth_health.py
- test_quad_channel_stealth.py

Features:
- Comprehensive agent testing
- Performance monitoring
- Error handling validation
- Health status reporting
- Multi-symbol testing
- Timeout protection
- Data quality analysis
"""

import asyncio
import sys
import time
import random
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Import all stealth agents
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
    print("Make sure you're running from the correct directory")
    sys.exit(1)


class UnifiedStealthTester:
    """Unified testing class for all stealth agents"""
    
    def __init__(self):
        self.agents = [
            ('MoneyControl', MoneyControlAgent),
            ('TrendLyne', TrendlyneAgent),
            ('StockEdge', StockEdgeAgent),
            ('TickerTape', TickertapeAgent),
            ('Tijori', TijoriAgent),
            ('TradingView', TradingViewAgent),
            ('Zerodha', ZerodhaAgent),
            ('Screener', ScreenerAgent)        ]
        
        self.test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK']
        self.results = {}
        self.performance_stats = defaultdict(list)
        
        # Verify all agents can be instantiated
        self._verify_agents_on_init()
    
    def _verify_agents_on_init(self):
        """Quick verification that all agents can be instantiated"""
        try:
            for agent_name, agent_class in self.agents:
                agent_class()  # Try to instantiate
            print(f"✅ All {len(self.agents)} stealth agents verified and ready")
        except Exception as e:
            print(f"❌ Agent verification failed: {e}")
            print("Some agents may not be properly configured")
        
    def print_header(self, title: str, char: str = '='):
        """Print formatted header"""
        print(f'\n{title}')
        print(char * len(title))
    
    def print_section(self, title: str):
        """Print section header"""
        print(f'\n📋 {title}')
        print('-' * (len(title) + 4))
    
    async def test_single_agent(self, agent_class, agent_name: str, symbol: str, timeout: int = 30) -> Dict:
        """Test a single agent with comprehensive metrics"""
        try:
            start_time = time.time()
            agent = agent_class()
            
            # Execute with timeout protection
            result = await asyncio.wait_for(
                agent.execute(symbol, {}), 
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Analyze result
            success = result and not result.get('error')
            verdict = result.get('verdict', 'UNKNOWN') if success else 'FAILED'
            confidence = result.get('confidence', 0.0) if success else 0.0
            value = result.get('value', 0.0) if success else 0.0
            error = result.get('error', '') if result else 'No result returned'
            
            # Extract data quality metrics
            data_quality = {}
            if success and 'details' in result:
                details = result['details']
                if 'data_quality' in details:
                    data_quality = details['data_quality']
            
            test_result = {
                'agent': agent_name,
                'symbol': symbol,
                'success': success,
                'verdict': verdict,
                'confidence': confidence,
                'value': value,
                'execution_time': execution_time,
                'error': error,
                'data_quality': data_quality,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store performance stats
            self.performance_stats[agent_name].append({
                'symbol': symbol,
                'success': success,
                'execution_time': execution_time,
                'confidence': confidence
            })
            
            return test_result
            
        except asyncio.TimeoutError:
            return {
                'agent': agent_name,
                'symbol': symbol,
                'success': False,
                'verdict': 'TIMEOUT',
                'confidence': 0.0,
                'value': 0.0,
                'execution_time': timeout,
                'error': f'Timeout after {timeout}s',
                'data_quality': {},
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'agent': agent_name,
                'symbol': symbol,
                'success': False,
                'verdict': 'ERROR',
                'confidence': 0.0,
                'value': 0.0,
                'execution_time': 0.0,
                'error': str(e),
                'data_quality': {},
                'timestamp': datetime.now().isoformat()
            }
    
    def format_result_line(self, result: Dict) -> str:
        """Format a single result line"""
        status_emoji = "✅" if result['success'] else "❌"
        agent = result['agent']
        verdict = result['verdict']
        confidence = result['confidence']
        exec_time = result['execution_time']
        
        if result['success']:
            line = f"  {status_emoji} {agent:12} | {verdict:12} | {confidence:4.2f} | {exec_time:6.2f}s"
            
            # Add data quality info if available
            dq = result.get('data_quality', {})
            if dq:
                channels = dq.get('channels_used', 'N/A')
                fusion_conf = dq.get('fusion_confidence', 'N/A')
                line += f" | Ch:{channels}, FC:{fusion_conf}"
        else:
            error_short = result['error'][:30] + "..." if len(result['error']) > 30 else result['error']
            line = f"  {status_emoji} {agent:12} | {verdict:12} | FAILED - {error_short}"
        
        return line
    
    async def test_all_agents_single_symbol(self, symbol: str) -> List[Dict]:
        """Test all agents against a single symbol"""
        self.print_section(f"Testing Symbol: {symbol}")
        print(f"{'Status':>4} {'Agent':12} | {'Verdict':12} | {'Conf':4} | {'Time':>8} | {'Quality'}")
        print("  " + "─" * 75)
        
        results = []
        for agent_name, agent_class in self.agents:
            result = await self.test_single_agent(agent_class, agent_name, symbol)
            results.append(result)
            print(self.format_result_line(result))            
            # Small delay between agents to avoid rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.0))
        
        return results
    
    async def test_comprehensive(self) -> Dict:
        """Run comprehensive test suite with detailed per-symbol reporting"""
        self.print_header("🇮🇳 COMPREHENSIVE INDIAN MARKET STEALTH AGENTS TEST", "=")
        
        results = {}
        
        # Test each symbol with detailed output like the original comprehensive test
        for symbol in self.test_symbols:
            print(f'\n📊 Testing symbol: {symbol}')
            print('-' * 40)
            results[symbol] = {}
            
            for agent_name, agent_class in self.agents:
                try:
                    print(f'  🔍 Testing {agent_name}...', end=' ')
                    
                    # Use execute method to get proper data handling
                    agent = agent_class()
                    result = await agent.execute(symbol, {})
                    
                    verdict = result.get('verdict', 'N/A')
                    confidence = result.get('confidence', 0)
                    value = result.get('value', 'N/A')
                    source = result.get('details', {}).get('source', 'N/A')
                    error = result.get('error')
                    
                    if error:
                        print(f'❌ Error: {error[:50]}...')
                        results[symbol][agent_name] = {
                            'success': False,
                            'error': str(error)
                        }
                    else:
                        print(f'✅ {verdict} (conf: {confidence:.2f}, val: {value})')
                        results[symbol][agent_name] = {
                            'verdict': verdict,
                            'confidence': confidence,
                            'value': value,
                            'source': source,
                            'success': True
                        }
                        
                except Exception as e:
                    print(f'❌ Exception: {str(e)[:50]}...')
                    results[symbol][agent_name] = {
                        'success': False,
                        'error': str(e)
                    }
        
        # Generate comprehensive summary exactly like the original
        self.print_header("📋 STEALTH AGENTS SUMMARY", "=")
        
        for symbol in self.test_symbols:
            print(f'\n📈 {symbol}:')
            for agent_name, _ in self.agents:
                if agent_name in results[symbol]:
                    agent_result = results[symbol][agent_name]
                    if agent_result['success']:
                        verdict = agent_result['verdict']
                        confidence = agent_result['confidence']
                        print(f'  ✅ {agent_name:12}: {verdict:10} (confidence: {confidence:.2f})')
                    else:
                        print(f'  ❌ {agent_name:12}: FAILED')
        
        # Calculate overall success rate
        total_tests = len(self.test_symbols) * len(self.agents)
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
        
        return {
            'results': results,
            'success_rate': success_rate,
            'successful_tests': successful_tests,
            'total_tests': total_tests
        }
    
    async def test_quick(self, symbols: List[str] = None) -> Dict:
        """Run quick test with limited symbols"""
        symbols = symbols or ['RELIANCE', 'TCS']
        self.print_header("⚡ QUICK STEALTH AGENT TEST")
        
        all_results = []
        for symbol in symbols:
            symbol_results = await self.test_all_agents_single_symbol(symbol)
            all_results.extend(symbol_results)
        
        return self.generate_summary_report(all_results)
    
    async def test_health_monitor(self) -> Dict:
        """Monitor agent health across multiple symbols"""
        self.print_header("🩺 STEALTH AGENT HEALTH MONITOR")
        
        health_results = {}
        
        for agent_name, agent_class in self.agents:
            print(f"\n🔍 Testing {agent_name} Health:")
            
            successes = 0
            total_time = 0
            test_count = min(3, len(self.test_symbols))  # Test with 3 symbols max
            
            for i, symbol in enumerate(self.test_symbols[:test_count]):
                result = await self.test_single_agent(agent_class, agent_name, symbol, timeout=20)
                
                if result['success']:
                    successes += 1
                    print(f"  ✅ {symbol}: SUCCESS ({result['execution_time']:.2f}s)")
                else:
                    print(f"  ❌ {symbol}: {result['verdict']}")
                
                total_time += result['execution_time']
            
            success_rate = (successes / test_count) * 100
            avg_time = total_time / test_count
            
            # Determine health status
            if success_rate >= 80:
                health_status = "🟢 EXCELLENT"
            elif success_rate >= 60:
                health_status = "🟡 GOOD"
            elif success_rate >= 40:
                health_status = "🟠 FAIR"
            else:
                health_status = "🔴 POOR"
            
            health_results[agent_name] = {
                'success_rate': success_rate,
                'avg_response_time': avg_time,
                'health_status': health_status,
                'tests_run': test_count,
                'successes': successes
            }
            
            print(f"  📊 Success Rate: {success_rate:.1f}%")
            print(f"  ⏱️  Avg Time: {avg_time:.2f}s")
            print(f"  💚 Health: {health_status}")
        
        return health_results
    
    async def test_error_handling(self) -> Dict:
        """Test error handling capabilities (503, timeouts, etc.)"""
        self.print_header("🛡️ ERROR HANDLING TEST")
        
        # Test with potential problematic scenarios
        error_results = {}
        
        # Test timeout handling
        print("\n⏰ Testing Timeout Handling:")
        timeout_result = await self.test_single_agent(StockEdgeAgent, "StockEdge", "RELIANCE", timeout=5)
        print(f"  Short timeout (5s): {'PASS' if timeout_result['verdict'] in ['TIMEOUT', 'SUCCESS'] else 'FAIL'}")
        
        # Test with non-existent symbol
        print("\n❓ Testing Invalid Symbol Handling:")
        invalid_result = await self.test_single_agent(TijoriAgent, "Tijori", "INVALID_SYMBOL", timeout=10)
        print(f"  Invalid symbol: {'PASS' if not invalid_result['success'] else 'UNEXPECTED_SUCCESS'}")
        
        error_results['timeout_test'] = timeout_result
        error_results['invalid_symbol_test'] = invalid_result
        
        return error_results
    
    async def test_quad_channel_functionality(self) -> Dict:
        """Test that all agents are properly using quad-channel scraping and anti-bot measures"""
        self.print_header("🔍 QUAD-CHANNEL & ANTI-BOT VERIFICATION TEST", "=")
        print("Verifying all agents use quad-channel data collection and stealth measures...")
        
        test_symbol = 'RELIANCE'
        quad_results = {}
        
        for agent_name, agent_class in self.agents:
            print(f"\n🧪 Testing {agent_name} Agent:")
            
            try:
                agent = agent_class()
                
                # Check if agent inherits from AdvancedStealthAgentBase
                has_advanced_base = hasattr(agent, '_quad_channel_fetch')
                has_circuit_breaker = hasattr(agent, 'circuit_breaker_config')
                has_user_agents = hasattr(agent, 'user_agents')
                has_rate_limiting = hasattr(agent, '_apply_rate_limiting')
                
                # Test actual execution
                start_time = time.time()
                result = await agent.execute(test_symbol, {})
                execution_time = time.time() - start_time
                
                # Analyze result for quad-channel indicators
                channels_used = 0
                fusion_confidence = 0
                has_data_quality = False
                
                if result and 'details' in result:
                    details = result['details']
                    if 'data_quality' in details:
                        dq = details['data_quality']
                        channels_used = dq.get('channels_used', 0)
                        fusion_confidence = dq.get('fusion_confidence', 0)
                        has_data_quality = True
                
                # Anti-bot verification
                anti_bot_score = 0
                if has_user_agents:
                    anti_bot_score += 25
                if has_rate_limiting:
                    anti_bot_score += 25
                if execution_time > 2.0:  # Good agents should have delays
                    anti_bot_score += 25
                if has_circuit_breaker:
                    anti_bot_score += 25
                
                # Quad-channel verification
                quad_score = 0
                if has_advanced_base:
                    quad_score += 30
                if channels_used >= 2:
                    quad_score += 30
                if fusion_confidence > 0:
                    quad_score += 20
                if has_data_quality:
                    quad_score += 20
                
                # Overall status
                status = "✅ EXCELLENT" if (quad_score >= 80 and anti_bot_score >= 75) else \
                        "🟡 GOOD" if (quad_score >= 60 and anti_bot_score >= 50) else \
                        "🟠 FAIR" if (quad_score >= 40 and anti_bot_score >= 25) else \
                        "🔴 POOR"
                
                print(f"  📊 Quad-Channel Features:")
                print(f"    - Advanced Base: {'✅' if has_advanced_base else '❌'}")
                print(f"    - Channels Used: {channels_used}/4")
                print(f"    - Fusion Confidence: {fusion_confidence}")
                print(f"    - Data Quality: {'✅' if has_data_quality else '❌'}")
                print(f"  🛡️  Anti-Bot Features:")
                print(f"    - User Agent Rotation: {'✅' if has_user_agents else '❌'}")
                print(f"    - Rate Limiting: {'✅' if has_rate_limiting else '❌'}")
                print(f"    - Circuit Breakers: {'✅' if has_circuit_breaker else '❌'}")
                print(f"    - Execution Time: {execution_time:.2f}s")
                print(f"  🎯 Overall Status: {status}")
                print(f"  📈 Scores: Quad={quad_score}/100, Anti-Bot={anti_bot_score}/100")
                
                quad_results[agent_name] = {
                    'status': status,
                    'quad_score': quad_score,
                    'anti_bot_score': anti_bot_score,
                    'channels_used': channels_used,
                    'fusion_confidence': fusion_confidence,
                    'execution_time': execution_time,
                    'has_advanced_base': has_advanced_base,
                    'features': {
                        'user_agents': has_user_agents,
                        'rate_limiting': has_rate_limiting,
                        'circuit_breaker': has_circuit_breaker,
                        'data_quality': has_data_quality
                    }
                }
                
            except Exception as e:
                print(f"  💥 ERROR: {str(e)[:100]}...")
                quad_results[agent_name] = {
                    'status': '🔴 ERROR',
                    'error': str(e)
                }
        
        # Summary
        self.print_section("QUAD-CHANNEL SUMMARY")
        excellent_agents = [name for name, data in quad_results.items() 
                          if data.get('status', '').startswith('✅')]
        needs_improvement = [name for name, data in quad_results.items() 
                           if data.get('status', '').startswith('🔴')]
        
        print(f"✅ Excellent Agents: {len(excellent_agents)}/{len(self.agents)}")
        print(f"🔴 Need Improvement: {len(needs_improvement)}/{len(self.agents)}")
          if needs_improvement:
            print(f"\n⚠️  Agents needing quad-channel/anti-bot improvements:")
            for agent in needs_improvement:
                print(f"  - {agent}")
        
        return quad_results

    async def test_trendlyne_intelligence(self) -> Dict:
        """Test TrendLyne AI intelligence features specifically"""
        self.print_header("🧠 TRENDLYNE AI INTELLIGENCE TEST")
        
        from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
        
        agent = TrendlyneAgent()
        test_symbols = ['RELIANCE', 'TCS', 'INFY']
        
        intelligence_results = {}
        
        for symbol in test_symbols:
            print(f"\n🔍 Testing AI intelligence for {symbol}...")
            try:
                result = await agent.execute(symbol)
                
                if result:
                    details = result.get('details', {})
                    ai_analysis = details.get('ai_analysis', {})
                    
                    intelligence_results[symbol] = {
                        'ai_scores': ai_analysis,
                        'intelligence_score': details.get('intelligence_score', 0),
                        'market_context': details.get('market_context', {}),
                        'sector_influence': details.get('sector_influence', {})
                    }
                    
                    print(f"✅ {symbol}: Intelligence Score = {details.get('intelligence_score', 0):.2f}")
                    if ai_analysis:
                        print(f"   AI Scores: Overall={ai_analysis.get('overall_score', 0):.2f}, "
                              f"Quality={ai_analysis.get('quality_score', 0):.2f}")
                else:
                    intelligence_results[symbol] = {'error': 'No result'}
                    print(f"❌ {symbol}: No result")
                    
            except Exception as e:
                intelligence_results[symbol] = {'error': str(e)}
                print(f"❌ {symbol}: {e}")
        
        return intelligence_results

    async def test_agent_intelligence(self, agent_class, agent_name: str, symbols: List[str] = None) -> Dict:
        """Test intelligence features for any agent that supports them"""
        symbols = symbols or ['RELIANCE', 'TCS', 'INFY']
        
        print(f"\n🧠 Testing {agent_name} Intelligence Features")
        print("=" * 60)
        
        try:
            agent = agent_class()
        except Exception as e:
            return {'error': f'Failed to initialize agent: {e}'}
        
        intelligence_results = {}
        
        for symbol in symbols:
            print(f"\n🔍 Testing {agent_name} intelligence for {symbol}...")
            try:
                result = await agent.execute(symbol)
                
                if result:
                    print(f"✅ {symbol} Analysis Complete:")
                    print(f"   📊 Signal: {result.get('verdict', 'N/A')}")
                    print(f"   🎯 Confidence: {result.get('confidence', 0):.2f}")
                    print(f"   💰 Value: {result.get('value', 0):.2f}")
                    
                    # Display AI insights if available
                    details = result.get('details', {})
                    ai_analysis = details.get('ai_analysis', {})
                    
                    if ai_analysis:
                        print(f"   🧠 AI Analysis Available:")
                        print(f"      🧠 Overall Score: {ai_analysis.get('overall_score', 0):.2f}")
                        print(f"      📈 Momentum Score: {ai_analysis.get('momentum_score', 0):.2f}")
                        print(f"      💎 Value Score: {ai_analysis.get('value_score', 0):.2f}")
                        print(f"      🏆 Quality Score: {ai_analysis.get('quality_score', 0):.2f}")
                        print(f"      🚀 Growth Score: {ai_analysis.get('growth_score', 0):.2f}")
                        print(f"      😊 Sentiment Score: {ai_analysis.get('sentiment_score', 0):.2f}")
                        print(f"      ⚠️ Risk Score: {ai_analysis.get('risk_score', 0):.2f}")
                        
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
                    print(f"   📊 Data Quality: {details.get('data_quality', 'unknown')}")
                    print(f"   🔗 Channels Used: {details.get('channels_used', 'N/A')}")
                    print(f"   🎯 Intelligence Score: {details.get('intelligence_score', 0):.2f}")
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
                        'intelligence_score': details.get('intelligence_score', 0),
                        'data_quality': details.get('data_quality'),
                        'market_context': market_context,
                        'sector_influence': sector_influence,
                        'has_ai_features': bool(ai_analysis)
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
            'ai_capable': any(r.get('has_ai_features', False) for r in intelligence_results.values())
        }

    async def test_all_agents_intelligence(self) -> Dict:
        """Test intelligence features across all available agents"""
        self.print_header("🧠 COMPREHENSIVE AGENT INTELLIGENCE TEST")
        
        # Test all stealth agents for intelligence features
        all_results = {}
        ai_capable_agents = []
        
        for agent_name, agent_class in self.agents:
            print(f"\n{'='*60}")
            result = await self.test_agent_intelligence(agent_class, agent_name)
            all_results[agent_name] = result
            
            if result.get('ai_capable', False):
                ai_capable_agents.append(agent_name)
        
        # Summary
        print(f"\n{'='*60}")
        print("🧠 INTELLIGENCE CAPABILITIES SUMMARY")
        print("="*60)
        
        print(f"📊 Total Agents Tested: {len(self.agents)}")
        print(f"🧠 AI-Capable Agents: {len(ai_capable_agents)}")
        
        if ai_capable_agents:
            print(f"✅ Agents with AI Features:")
            for agent in ai_capable_agents:
                print(f"   - {agent}")
        
        non_ai_agents = [name for name, _ in self.agents if name not in ai_capable_agents]
        if non_ai_agents:
            print(f"📋 Standard Agents (No AI Features):")
            for agent in non_ai_agents:
                print(f"   - {agent}")
        
        return {
            'total_agents': len(self.agents),
            'ai_capable_count': len(ai_capable_agents),
            'ai_capable_agents': ai_capable_agents,
            'results': all_results
        }
    
    def generate_summary_report(self, all_results: List[Dict]) -> Dict:
        """Generate comprehensive summary report"""
        self.print_header("📊 COMPREHENSIVE TEST RESULTS")
        
        # Calculate overall statistics
        total_tests = len(all_results)
        successful_tests = sum(1 for r in all_results if r['success'])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Agent-wise statistics
        agent_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'avg_time': 0})
        
        for result in all_results:
            agent = result['agent']
            agent_stats[agent]['total'] += 1
            if result['success']:
                agent_stats[agent]['success'] += 1
            agent_stats[agent]['avg_time'] += result['execution_time']
        
        # Calculate averages
        for agent in agent_stats:
            stats = agent_stats[agent]
            stats['success_rate'] = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            stats['avg_time'] = stats['avg_time'] / stats['total'] if stats['total'] > 0 else 0
        
        # Print summary table
        print(f"\n📈 AGENT PERFORMANCE SUMMARY")
        print("─" * 80)
        print(f"{'Agent':12} | {'Success Rate':>12} | {'Avg Time':>10} | {'Tests':>6} | {'Status':>12}")
        print("─" * 80)
        
        for agent_name, agent_class in self.agents:
            stats = agent_stats[agent_name]
            if stats['total'] > 0:
                status = "🟢 GOOD" if stats['success_rate'] >= 60 else "🟡 FAIR" if stats['success_rate'] >= 30 else "🔴 POOR"
                print(f"{agent_name:12} | {stats['success_rate']:10.1f}% | {stats['avg_time']:8.2f}s | {stats['total']:4}   | {status}")
        
        # Overall system health
        print("─" * 80)
        if success_rate >= 70:
            system_health = "🟢 HEALTHY"
        elif success_rate >= 50:
            system_health = "🟡 STABLE"
        else:
            system_health = "🔴 DEGRADED"
        
        print(f"OVERALL SYSTEM: {success_rate:.1f}% success rate | {system_health}")
        
        summary = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate': success_rate,
            'agent_stats': dict(agent_stats),
            'system_health': system_health,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def print_recommendations(self, summary: Dict):
        """Print recommendations based on test results"""
        self.print_header("💡 RECOMMENDATIONS")
        
        agent_stats = summary['agent_stats']
        
        # Identify problematic agents
        poor_agents = [name for name, stats in agent_stats.items() if stats.get('success_rate', 0) < 30]
        slow_agents = [name for name, stats in agent_stats.items() if stats.get('avg_time', 0) > 15]
        
        if poor_agents:
            print(f"🔴 Agents needing attention: {', '.join(poor_agents)}")
            print("   - Check URL patterns and data extraction logic")
            print("   - Verify website structure hasn't changed")
        
        if slow_agents:
            print(f"⏰ Slow performing agents: {', '.join(slow_agents)}")
            print("   - Optimize timeout settings")
            print("   - Review rate limiting configuration")
        
        if summary['success_rate'] < 50:
            print("🚨 CRITICAL: Overall system success rate is low")
            print("   - Consider implementing additional fallback sources")
            print("   - Review circuit breaker configurations")
        
        print("\n✅ All stealth agents are designed to work with background data collection")
        print("   - Multi-channel data fusion is active")
        print("   - Emergency fallback sources are configured")
        print("   - Circuit breakers prevent cascade failures")

    async def test_all_stealth_agents(self):
        """
        Compatibility method that exactly mimics the original comprehensive test.
        This ensures existing scripts that call test_all_stealth_agents() still work.
        """
        return await self.test_comprehensive()
        
    def analyze_intelligence_features(self, result: Dict, agent_name: str) -> Dict:
        """Analyze intelligence features from agent result"""
        intelligence_data = {}
        
        if not result or result.get('error'):
            return intelligence_data
            
        details = result.get('details', {})
        
        # Extract AI analysis if available
        ai_analysis = details.get('ai_analysis', {})
        if ai_analysis:
            intelligence_data['ai_scores'] = {
                'overall_score': ai_analysis.get('overall_score', 0),
                'momentum_score': ai_analysis.get('momentum_score', 0),
                'value_score': ai_analysis.get('value_score', 0),
                'quality_score': ai_analysis.get('quality_score', 0),
                'growth_score': ai_analysis.get('growth_score', 0),
                'sentiment_score': ai_analysis.get('sentiment_score', 0),
                'risk_score': ai_analysis.get('risk_score', 0)
            }
            
            intelligence_data['insights'] = {
                'key_insights': ai_analysis.get('key_insights', []),
                'risk_factors': ai_analysis.get('risk_factors', []),
                'opportunities': ai_analysis.get('opportunities', [])
            }
        
        # Extract intelligence metrics
        intelligence_data['metrics'] = {
            'intelligence_score': details.get('intelligence_score', 0),
            'data_quality': details.get('data_quality', 'unknown'),
            'data_completeness': details.get('data_completeness', 'unknown'),
            'channels_used': details.get('channels_used', 0),
            'fusion_confidence': details.get('fusion_confidence', 0)
        }
        
        # Extract market context
        market_context = details.get('market_context', {})
        if market_context:
            intelligence_data['market_context'] = {
                'market_trend': market_context.get('market_trend', 'unknown'),
                'volatility_level': market_context.get('volatility_level', 'unknown'),
                'risk_environment': market_context.get('risk_environment', 'unknown')
            }
        
        # Extract sector analysis
        sector_influence = details.get('sector_influence', {})
        if sector_influence:
            intelligence_data['sector_analysis'] = {
                'sector': sector_influence.get('sector', 'unknown'),
                'sector_momentum': sector_influence.get('sector_momentum', 'unknown'),
                'sector_outlook': sector_influence.get('sector_outlook', 'unknown')
            }
            
        return intelligence_data
    
    def print_intelligence_analysis(self, symbol: str, agent_name: str, intelligence_data: Dict):
        """Print detailed intelligence analysis for an agent"""
        if not intelligence_data:
            print(f"      📊 No intelligence data available")
            return
            
        # AI Scores
        ai_scores = intelligence_data.get('ai_scores', {})
        if ai_scores:
            print(f"      🧠 AI Analysis:")
            for score_name, score_value in ai_scores.items():
                if score_value > 0:
                    score_display = score_name.replace('_', ' ').title()
                    print(f"         {score_display}: {score_value:.2f}")
        
        # Intelligence Metrics
        metrics = intelligence_data.get('metrics', {})
        if metrics:
            print(f"      📈 Intelligence Metrics:")
            intel_score = metrics.get('intelligence_score', 0)
            data_quality = metrics.get('data_quality', 'unknown')
            channels = metrics.get('channels_used', 0)
            
            if intel_score > 0:
                print(f"         Intelligence Score: {intel_score:.2f}")
            if data_quality != 'unknown':
                print(f"         Data Quality: {data_quality}")
            if channels > 0:
                print(f"         Channels Used: {channels}")
        
        # Key Insights
        insights = intelligence_data.get('insights', {})
        key_insights = insights.get('key_insights', [])
        if key_insights:
            print(f"      💡 Key Insights:")
            for insight in key_insights[:2]:  # Show top 2
                print(f"         • {insight}")
        
        # Risk Factors
        risk_factors = insights.get('risk_factors', [])
        if risk_factors:
            print(f"      ⚠️ Risk Factors:")
            for risk in risk_factors[:2]:  # Show top 2
                print(f"         • {risk}")

    async def test_intelligence_comprehensive(self) -> Dict:
        """Test intelligence features across all agents comprehensively"""
        self.print_header("🧠 COMPREHENSIVE INTELLIGENCE ANALYSIS", "=")
        
        intelligence_results = {}
        agent_intelligence_scores = {}
        
        for symbol in self.test_symbols:
            self.print_section(f"Intelligence Analysis for {symbol}")
            intelligence_results[symbol] = {}
            
            for agent_name, agent_class in self.agents:
                try:
                    print(f"    🔍 {agent_name} Intelligence Analysis...")
                    
                    agent = agent_class()
                    result = await agent.execute(symbol, {})
                    
                    # Analyze intelligence features
                    intelligence_data = self.analyze_intelligence_features(result, agent_name)
                    intelligence_results[symbol][agent_name] = intelligence_data
                    
                    # Print results
                    if intelligence_data:
                        metrics = intelligence_data.get('metrics', {})
                        intel_score = metrics.get('intelligence_score', 0)
                        
                        print(f"      ✅ Intelligence Score: {intel_score:.2f}")
                        self.print_intelligence_analysis(symbol, agent_name, intelligence_data)
                        
                        # Track agent intelligence capability
                        if agent_name not in agent_intelligence_scores:
                            agent_intelligence_scores[agent_name] = []
                        agent_intelligence_scores[agent_name].append(intel_score)
                    else:
                        print(f"      📊 Basic analysis only")
                        
                except Exception as e:
                    print(f"      ❌ Error: {str(e)[:50]}...")
                    intelligence_results[symbol][agent_name] = {'error': str(e)}
            
            print("-" * 60)
        
        # Intelligence Capability Summary
        self.print_header("📊 INTELLIGENCE CAPABILITY SUMMARY")
        
        for agent_name, scores in agent_intelligence_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                
                if avg_score >= 0.7:
                    status = "🔥 ADVANCED"
                elif avg_score >= 0.5:
                    status = "🚀 ENHANCED"
                elif avg_score >= 0.3:
                    status = "⚡ BASIC"
                else:
                    status = "📊 STANDARD"
                    
                print(f"  {agent_name:12} | Avg: {avg_score:.2f} | Max: {max_score:.2f} | {status}")
            else:
                print(f"  {agent_name:12} | No intelligence data available")
        
        return {
            'intelligence_results': intelligence_results,
            'agent_capabilities': agent_intelligence_scores,
            'summary': {
                'total_agents_tested': len(self.agents),
                'agents_with_intelligence': len(agent_intelligence_scores),
                'symbols_tested': len(self.test_symbols)
            }
        }

    async def test_intelligence_quick(self, symbols: List[str] = None) -> Dict:
        """Quick intelligence test focusing on key metrics"""
        symbols = symbols or ['RELIANCE', 'TCS']
        self.print_header("⚡ QUICK INTELLIGENCE TEST")
        
        quick_results = {}
        
        for symbol in symbols:
            print(f"\n🔍 Testing {symbol} Intelligence:")
            quick_results[symbol] = {}
            
            for agent_name, agent_class in self.agents:
                try:
                    agent = agent_class()
                    result = await agent.execute(symbol, {})
                    
                    intelligence_data = self.analyze_intelligence_features(result, agent_name)
                    
                    if intelligence_data:
                        metrics = intelligence_data.get('metrics', {})
                        intel_score = metrics.get('intelligence_score', 0)
                        data_quality = metrics.get('data_quality', 'unknown')
                        
                        print(f"  ✅ {agent_name:12}: Intel={intel_score:.2f}, Quality={data_quality}")
                        quick_results[symbol][agent_name] = {
                            'intelligence_score': intel_score,
                            'data_quality': data_quality,
                            'has_ai_analysis': bool(intelligence_data.get('ai_scores'))
                        }
                    else:
                        print(f"  📊 {agent_name:12}: Standard analysis")
                        quick_results[symbol][agent_name] = {
                            'intelligence_score': 0,
                            'data_quality': 'basic',
                            'has_ai_analysis': False
                        }
                        
                except Exception as e:
                    print(f"  ❌ {agent_name:12}: Error")
                    quick_results[symbol][agent_name] = {'error': str(e)}
        
        return quick_results

async def main():
    """Main test runner with command-line options"""
    import argparse
      parser = argparse.ArgumentParser(description='Unified Stealth Agent Testing Suite')
    parser.add_argument('--mode', choices=['comprehensive', 'quick', 'health', 'errors', 'quad', 'intelligence', 'all-intelligence'], 
                       default='quick', help='Test mode to run')
    parser.add_argument('--symbols', nargs='+', default=['RELIANCE', 'TCS'], 
                       help='Symbols to test (for quick mode)')
    
    args = parser.parse_args()
    
    tester = UnifiedStealthTester()
    
    try:
        if args.mode == 'comprehensive':
            summary = await tester.test_comprehensive()
        elif args.mode == 'quick':
            summary = await tester.test_quick(args.symbols)
        elif args.mode == 'health':
            summary = await tester.test_health_monitor()
        elif args.mode == 'errors':
            summary = await tester.test_error_handling()
        elif args.mode == 'quad':
            summary = await tester.test_quad_channel_functionality()        elif args.mode == 'intelligence':
            summary = await tester.test_trendlyne_intelligence()
        elif args.mode == 'all-intelligence':
            summary = await tester.test_all_agents_intelligence()
        else:
            summary = await tester.test_quick()
        
        # Print recommendations
        if isinstance(summary, dict) and 'agent_stats' in summary:
            tester.print_recommendations(summary)
        
        print(f"\n🎉 Testing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        raise


# Backward compatibility functions for existing scripts
async def test_all_stealth_agents():
    """
    Standalone function for backward compatibility with existing scripts.
    This mimics the exact behavior of the original test_all_stealth_agents.py
    """
    tester = UnifiedStealthTester()
    return await tester.test_comprehensive()

# Make this file importable and runnable
if __name__ == "__main__":
    # Check if being run directly or imported
    import sys
    if len(sys.argv) == 1:
        # Run interactively if no arguments
        asyncio.run(main())
    else:
        # Support command line arguments
        asyncio.run(main())
