#!/usr/bin/env python3
"""
Browser Support Installation Script for TrendLyne Agent
=====================================================

This script installs the necessary dependencies for headless browser support
in the TrendLyne stealth agent.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("🚀 Installing Browser Support for TrendLyne Agent")
    print("=" * 50)
    
    # Install Python packages
    packages = [
        "playwright>=1.40.0",
        "selenium>=4.15.0", 
        "undetected-chromedriver>=3.5.0",
        "selenium-stealth>=1.0.6",
        "fake-useragent>=1.4.0",
        "httpx[http2]>=0.25.0"
    ]
    
    for package in packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            print(f"⚠️ Failed to install {package}, continuing...")
    
    # Install Playwright browsers
    if run_command("playwright install chromium", "Installing Playwright Chromium browser"):
        print("✅ Playwright browser installed")
    else:
        print("⚠️ Playwright browser installation failed")
    
    # Install Chrome for Selenium (optional)
    print("\n📋 Additional Setup Notes:")
    print("=" * 30)
    print("1. For best results, ensure Google Chrome is installed on your system")
    print("2. The TrendLyne agent will automatically fallback to HTTP client if browsers fail")
    print("3. Headless browsers provide better JavaScript support and anti-bot evasion")
    
    print("\n🎯 Testing Browser Installation...")
    print("=" * 35)
    
    # Test Playwright
    try:
        import playwright
        print("✅ Playwright imported successfully")
    except ImportError:
        print("❌ Playwright import failed")
    
    # Test Selenium
    try:
        import selenium
        print("✅ Selenium imported successfully")
    except ImportError:
        print("❌ Selenium import failed")
    
    print("\n🚀 Browser support installation complete!")
    print("You can now use advanced headless browser features in the TrendLyne agent.")

if __name__ == "__main__":
    main()
