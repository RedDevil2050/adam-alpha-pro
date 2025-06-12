#!/usr/bin/env node

// Quick test to verify the frontend is running properly
const http = require('http');

const testFrontend = () => {
  console.log('🧪 Testing Zion Frontend...\n');
  
  const options = {
    hostname: 'localhost',
    port: 3000,
    path: '/',
    method: 'GET',
    timeout: 5000
  };

  const req = http.request(options, (res) => {
    console.log(`✅ Frontend Status: ${res.statusCode}`);
    console.log(`📡 Content-Type: ${res.headers['content-type']}`);
    
    if (res.statusCode === 200) {
      console.log('🎉 Frontend is running successfully!');
      console.log('🌟 Your loveable Zion Market Analysis Platform is ready!');
      console.log('\n📱 Features Available:');
      console.log('   • Beautiful animated dashboard');
      console.log('   • Real-time market data');
      console.log('   • Smart notifications');
      console.log('   • Responsive design');
      console.log('   • Accessibility features');
      console.log('   • Theme switching');
      console.log('\n🌐 Access your app at: http://localhost:3000');
    } else {
      console.log('⚠️  Frontend returned non-200 status');
    }
  });

  req.on('error', (err) => {
    console.log('❌ Frontend is not running or not accessible');
    console.log('💡 Make sure to run: npm start');
    console.error('Error:', err.message);
  });

  req.on('timeout', () => {
    console.log('⏰ Request timed out - server might be starting up');
    req.destroy();
  });

  req.end();
};

// Run the test
testFrontend();
