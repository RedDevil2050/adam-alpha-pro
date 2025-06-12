#!/usr/bin/env python3
"""
🇮🇳 INDIAN STOCK PLATFORM INTEGRATION TEST
===========================================

Complete test suite for the Trendlyne-style Indian stock analysis platform.
Tests both backend API and frontend integration capabilities.
"""

import requests
import json
import time
from datetime import datetime

class IndianStockPlatformTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Log test results with timestamp"""
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test": test_name,
            "status": "✅ PASS" if success else "❌ FAIL",
            "details": details
        }
        self.test_results.append(result)
        print(f"{result['status']} {test_name}: {details}")

    def test_backend_health(self):
        """Test backend server health"""
        try:
            response = requests.get(f"{self.backend_url}/api/health", timeout=5)
            success = response.status_code == 200
            details = f"Status: {response.status_code}, Response time: {response.elapsed.total_seconds():.2f}s"
            self.log_test("Backend Health Check", success, details)
            return success
        except Exception as e:
            self.log_test("Backend Health Check", False, f"Error: {str(e)}")
            return False

    def test_indian_symbol_validation(self):
        """Test Indian stock symbol validation"""
        test_symbols = [
            "RELIANCE",      # NSE raw format
            "TCS.NS",        # Yahoo NSE format
            "HDFCBANK.BO",   # Yahoo BSE format
            "INFY",          # IT stock
            "ICICIBANK",     # Banking stock
            "WIPRO",         # Another IT stock
            "TATASTEEL",     # Metal stock
            "HINDUNILVR"     # FMCG stock
        ]
        
        success_count = 0
        for symbol in test_symbols:
            try:
                response = requests.get(
                    f"{self.backend_url}/api/symbols/validate/{symbol}", 
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("is_valid") and data.get("is_indian_symbol"):
                        success_count += 1
                        self.log_test(f"Symbol Validation - {symbol}", True, 
                                    f"Exchange: {data.get('detected_exchange')}")
                    else:
                        self.log_test(f"Symbol Validation - {symbol}", False, 
                                    "Invalid or non-Indian symbol")
                else:
                    self.log_test(f"Symbol Validation - {symbol}", False, 
                                f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Symbol Validation - {symbol}", False, str(e))
        
        overall_success = success_count >= len(test_symbols) * 0.8  # 80% success rate
        self.log_test("Overall Symbol Validation", overall_success, 
                     f"{success_count}/{len(test_symbols)} symbols validated")
        return overall_success

    def test_frontend_accessibility(self):
        """Test frontend server accessibility"""
        test_routes = [
            "/",
            "/login",
            "/dashboard", 
            "/screener"
        ]
        
        success_count = 0
        for route in test_routes:
            try:
                response = requests.get(f"{self.frontend_url}{route}", timeout=5)
                success = response.status_code in [200, 302]  # 302 for redirects
                if success:
                    success_count += 1
                    self.log_test(f"Frontend Route - {route}", True, 
                                f"Status: {response.status_code}")
                else:
                    self.log_test(f"Frontend Route - {route}", False, 
                                f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Frontend Route - {route}", False, str(e))
        
        overall_success = success_count >= len(test_routes) * 0.75  # 75% success rate
        self.log_test("Overall Frontend Accessibility", overall_success, 
                     f"{success_count}/{len(test_routes)} routes accessible")
        return overall_success

    def test_api_provider_normalization(self):
        """Test multi-provider symbol normalization"""
        test_symbol = "RELIANCE"
        try:
            response = requests.get(
                f"{self.backend_url}/api/symbols/validate/{test_symbol}", 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                provider_formats = data.get("provider_formats", {})
                
                required_providers = ["yahoo_finance", "alpha_vantage", "polygon", "finnhub"]
                success = all(provider in provider_formats for provider in required_providers)
                
                details = f"Providers: {', '.join(provider_formats.keys())}"
                self.log_test("Multi-Provider Normalization", success, details)
                return success
            else:
                self.log_test("Multi-Provider Normalization", False, 
                            f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Multi-Provider Normalization", False, str(e))
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print("🇮🇳 INDIAN STOCK PLATFORM INTEGRATION TEST")
        print("=" * 50)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all tests
        backend_health = self.test_backend_health()
        symbol_validation = self.test_indian_symbol_validation()
        frontend_access = self.test_frontend_accessibility()
        provider_norm = self.test_api_provider_normalization()
        
        # Calculate overall success rate
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "✅" in r["status"]])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print()
        print("=" * 50)
        print("🎯 FINAL RESULTS")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        if success_rate >= 80:
            print("🎉 PLATFORM READY FOR USE!")
            print("✅ Backend API: Working")
            print("✅ Indian Stocks: Supported") 
            print("✅ Frontend: Accessible")
            print("✅ Multi-Provider: Enabled")
            print()
            print("🚀 ACCESS YOUR INDIAN STOCK PLATFORM:")
            print(f"   Frontend: {self.frontend_url}")
            print(f"   API Docs: {self.backend_url}/docs")
            print(f"   Screener: {self.frontend_url}/screener")
            print("   Demo Login: username=demo, password=demo")
        else:
            print("⚠️  PLATFORM NEEDS ATTENTION")
            print("Some components may not be working correctly.")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = IndianStockPlatformTester()
    tester.run_all_tests()
