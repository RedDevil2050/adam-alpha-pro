#!/usr/bin/env python3
"""
🚀 Enhanced TrendLyne Agent Intelligence Test
Tests the AI-powered analysis capabilities
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
from loguru import logger

async def test_enhanced_intelligence():
    """Test enhanced AI intelligence features"""
    
    print("\n" + "="*60)
    print("🧠 ENHANCED TRENDLYNE AGENT INTELLIGENCE TEST")
    print("="*60)
    
    agent = TrendlyneAgent()
    
    # Test multiple symbols for comprehensive analysis
    test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ITC']
    
    for symbol in test_symbols:
        print(f"\n🔍 Testing enhanced intelligence for {symbol}...")
        try:
            result = await agent.execute(symbol)
            
            if result:
                print(f"✅ {symbol} Analysis Complete:")
                print(f"   📊 Signal: {result.get('verdict', 'N/A')}")
                print(f"   🎯 Confidence: {result.get('confidence', 0):.2f}")
                print(f"   💰 Tradability: {result.get('value', 0):.2f}")
                
                # Display AI insights
                details = result.get('details', {})
                ai_analysis = details.get('ai_analysis', {})
                
                if ai_analysis:
                    print(f"   🧠 AI Overall Score: {ai_analysis.get('overall_score', 0):.2f}")
                    print(f"   📈 Momentum Score: {ai_analysis.get('momentum_score', 0):.2f}")
                    print(f"   💎 Value Score: {ai_analysis.get('value_score', 0):.2f}")
                    print(f"   🏆 Quality Score: {ai_analysis.get('quality_score', 0):.2f}")
                    print(f"   🚀 Growth Score: {ai_analysis.get('growth_score', 0):.2f}")
                    print(f"   😊 Sentiment Score: {ai_analysis.get('sentiment_score', 0):.2f}")
                    print(f"   ⚠️ Risk Score: {ai_analysis.get('risk_score', 0):.2f}")
                    
                    # Key insights
                    insights = ai_analysis.get('key_insights', [])
                    if insights:
                        print(f"   💡 Key Insights:")
                        for insight in insights[:3]:
                            print(f"      - {insight}")
                    
                    # Risk factors
                    risks = ai_analysis.get('risk_factors', [])
                    if risks:
                        print(f"   ⚠️ Risk Factors:")
                        for risk in risks[:2]:
                            print(f"      - {risk}")
                    
                    # Opportunities
                    opportunities = ai_analysis.get('opportunities', [])
                    if opportunities:
                        print(f"   🌟 Opportunities:")
                        for opp in opportunities[:2]:
                            print(f"      - {opp}")
                
                # Technical details
                print(f"   📊 Data Quality: {details.get('data_quality', 'unknown')}")
                print(f"   🔗 Channels Used: {details.get('channels_used', 0)}")
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
                
            else:
                print(f"❌ {symbol}: No result returned")
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
        
        print("-" * 40)
    
    print(f"\n✅ Enhanced Intelligence Test Complete!")
    print("🧠 AI-powered analysis provides:")
    print("   • Multi-factor scoring system")
    print("   • Intelligent signal generation")
    print("   • Risk-adjusted recommendations")
    print("   • Market context awareness")
    print("   • Sector-specific insights")
    print("   • Dynamic confidence calculation")
    print("   • Comprehensive risk assessment")

if __name__ == "__main__":
    asyncio.run(test_enhanced_intelligence())
