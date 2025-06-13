#!/usr/bin/env python3
"""
Debug script to find and fix selector issues in stealth agents
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_css_selectors():
    """Validate CSS selectors to find issues"""
    import re
    
    # Invalid patterns to look for
    invalid_patterns = [
        r',,',  # Double commas
        r'\.\.', # Double dots  
        r'voolume', # Typos
        r'maarket_cap',
        r'pee_ratio', 
        r'hiigh',
        r'loow'
    ]
    
    issues_found = []
    
    # Check stealth agent files
    stealth_dir = project_root / "backend" / "agents" / "stealth"
    
    for py_file in stealth_dir.glob("*.py"):
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        for line_num, line in enumerate(lines, 1):
            for pattern in invalid_patterns:
                if re.search(pattern, line):
                    issues_found.append({
                        'file': py_file.name,
                        'line': line_num,
                        'content': line.strip(),
                        'pattern': pattern
                    })
    
    return issues_found

def test_agent_imports():
    """Test if all agents can be imported"""
    try:
        from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
        from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
        from backend.agents.stealth.stockedge_agent import StockEdgeAgent
        from backend.agents.stealth.tickertape_agent import TickertapeAgent
        from backend.agents.stealth.tijori_agent import TijoriAgent
        from backend.agents.stealth.tradingview_agent import TradingViewAgent
        from backend.agents.stealth.zerodha_agent import ZerodhaAgent
        from backend.agents.stealth.screener_agent import ScreenerAgent
        
        agents = [
            ('MoneyControl', MoneyControlAgent),
            ('TrendLyne', TrendlyneAgent),
            ('StockEdge', StockEdgeAgent),
            ('TickerTape', TickertapeAgent),
            ('Tijori', TijoriAgent),
            ('TradingView', TradingViewAgent),
            ('Zerodha', ZerodhaAgent),
            ('Screener', ScreenerAgent)
        ]
        
        print("✅ Agent Import Test Results:")
        for name, agent_class in agents:
            try:
                agent = agent_class()
                print(f"  ✅ {name}: OK")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def check_selenium_setup():
    """Check if selenium and webdriver setup is working"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("✅ Selenium imports successful")
        
        # Test webdriver manager
        try:
            driver_path = ChromeDriverManager().install()
            print(f"✅ ChromeDriver available at: {driver_path}")
            return True
        except Exception as e:
            print(f"❌ ChromeDriver setup failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Selenium imports failed: {e}")
        return False

def main():
    """Main debug function"""
    print("🔍 STEALTH AGENT DEBUGGING")
    print("=" * 50)
    
    # Check CSS selectors
    print("\n1. Checking CSS selectors...")
    issues = validate_css_selectors()
    if issues:
        print("❌ CSS Selector Issues Found:")
        for issue in issues:
            print(f"  File: {issue['file']} Line {issue['line']}")
            print(f"  Pattern: {issue['pattern']}")
            print(f"  Content: {issue['content']}")
            print()
    else:
        print("✅ No CSS selector issues found in code")
    
    # Check imports
    print("\n2. Testing agent imports...")
    import_success = test_agent_imports()
    
    # Check selenium
    print("\n3. Testing Selenium setup...")
    selenium_success = check_selenium_setup()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 SUMMARY:")
    print(f"  CSS Issues: {'❌' if issues else '✅'}")
    print(f"  Agent Imports: {'✅' if import_success else '❌'}")
    print(f"  Selenium Setup: {'✅' if selenium_success else '❌'}")
    
    if not issues and import_success and selenium_success:
        print("\n🎉 All checks passed! Ready to run stealth tests.")
    else:
        print("\n⚠️  Issues found. Fix them before running tests.")

if __name__ == "__main__":
    main()
