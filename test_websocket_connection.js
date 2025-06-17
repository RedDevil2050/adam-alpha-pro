// Simple WebSocket connection test
const WebSocket = require('ws');

const wsUrl = 'ws://localhost:8000/api/stealth/stream';

console.log('🔌 Testing WebSocket connection to:', wsUrl);

const ws = new WebSocket(wsUrl);

ws.on('open', function open() {
  console.log('✅ WebSocket connection established!');
  
  // Subscribe to some symbols
  const subscribeMessage = {
    type: 'subscribe',
    symbol: 'RELIANCE'
  };
  
  ws.send(JSON.stringify(subscribeMessage));
  console.log('📊 Subscribed to RELIANCE');
});

ws.on('message', function message(data) {
  try {
    const parsedData = JSON.parse(data);
    console.log('📨 Received data:', parsedData);
  } catch (error) {
    console.log('📨 Received raw data:', data.toString());
  }
});

ws.on('close', function close() {
  console.log('🔌 WebSocket connection closed');
});

ws.on('error', function error(err) {
  console.error('❌ WebSocket error:', err.message);
});

// Keep the connection alive for 10 seconds
setTimeout(() => {
  console.log('⏰ Closing test connection...');
  ws.close();
}, 10000);
