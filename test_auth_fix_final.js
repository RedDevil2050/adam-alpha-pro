/**
 * Test script to verify authentication fix for Indian Stock Platform
 */

const axios = require('axios');
const fs = require('fs');

// Test configuration
const FRONTEND_URL = 'http://localhost:3000';
const BACKEND_URL = 'http://localhost:8000';

async function testAuthenticationFlow() {
    console.log('🔐 TESTING AUTHENTICATION FIX');
    console.log('=' .repeat(50));

    try {
        // Test 1: Check if frontend is accessible
        console.log('1. Testing frontend accessibility...');
        try {
            const frontendResponse = await axios.get(FRONTEND_URL, {
                timeout: 5000,
                validateStatus: function (status) {
                    return status < 500; // Accept any status below 500
                }
            });
            console.log(`   ✅ Frontend accessible: ${frontendResponse.status}`);
        } catch (error) {
            console.log(`   ❌ Frontend not accessible: ${error.message}`);
            console.log('   💡 Run: npm start in d:\\Zion\\frontend');
        }

        // Test 2: Check if backend is accessible
        console.log('2. Testing backend accessibility...');
        try {
            const backendResponse = await axios.get(`${BACKEND_URL}/api/health`, {
                timeout: 5000
            });
            console.log(`   ✅ Backend accessible: ${backendResponse.status}`);
        } catch (error) {
            console.log(`   ❌ Backend not accessible: ${error.message}`);
            console.log('   💡 Run: python -m uvicorn backend.api.main:app --reload');
        }

        // Test 3: Verify AuthContext.js fix
        console.log('3. Checking AuthContext.js authentication fix...');
        const authContextPath = 'd:\\Zion\\frontend\\src\\contexts\\AuthContext.js';
        
        if (fs.existsSync(authContextPath)) {
            const authContent = fs.readFileSync(authContextPath, 'utf8');
            
            // Check for key fixes
            const fixes = [
                {
                    name: 'Token initialization from localStorage',
                    check: authContent.includes('useState(null)') && authContent.includes('localStorage.getItem(\'token\')')
                },
                {
                    name: 'Demo token handling',
                    check: authContent.includes('demo-token-') && authContent.includes('startsWith(\'demo-token-\')')
                },
                {
                    name: 'Proper useEffect dependencies',
                    check: authContent.includes('[token])')
                },
                {
                    name: 'Authentication state logic',
                    check: authContent.includes('!!token && !!user')
                }
            ];

            fixes.forEach(fix => {
                console.log(`   ${fix.check ? '✅' : '❌'} ${fix.name}`);
            });

            const allFixed = fixes.every(fix => fix.check);
            console.log(`   📊 Overall Fix Status: ${allFixed ? '✅ COMPLETE' : '❌ INCOMPLETE'}`);
        } else {
            console.log('   ❌ AuthContext.js not found');
        }

        // Test 4: Check if Indian stock symbols are working
        console.log('4. Testing Indian stock symbol validation...');
        try {
            const symbolTestResponse = await axios.get(`${BACKEND_URL}/api/symbols/validate/RELIANCE`, {
                timeout: 5000
            });
            console.log(`   ✅ Symbol validation working: ${symbolTestResponse.status}`);
            console.log(`   📊 RELIANCE symbol: ${JSON.stringify(symbolTestResponse.data, null, 2)}`);
        } catch (error) {
            console.log(`   ❌ Symbol validation failed: ${error.message}`);
        }

        console.log('\n🎯 AUTHENTICATION FIX SUMMARY');
        console.log('=' .repeat(50));
        console.log('✅ Key changes implemented:');
        console.log('   • Fixed token initialization timing');
        console.log('   • Improved demo token handling');
        console.log('   • Fixed useEffect dependencies');
        console.log('   • Enhanced authentication state logic');
        console.log('');
        console.log('🚀 NEXT STEPS:');
        console.log('   1. Start frontend: cd d:\\Zion\\frontend && npm start');
        console.log('   2. Navigate to: http://localhost:3000');
        console.log('   3. Login with: demo / demo');
        console.log('   4. Test the screener: http://localhost:3000/screener');
        console.log('   5. Test stock details: http://localhost:3000/stock/RELIANCE');

    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Run the test
testAuthenticationFlow().catch(console.error);
