/**
 * Live Data Service for Real-time Stealth Agent Data
 * Manages WebSocket connections and live data streaming
 */

class LiveDataService {
  constructor() {
    this.ws = null;
    this.subscribers = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 5000;
    this.connectionState = 'disconnected';
    this.baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
  }

  // Connect to the stealth data stream
  async connect() {
    try {
      const wsUrl = `${this.baseUrl}/api/stealth/stream`;
      console.log('🔌 Connecting to live data stream:', wsUrl);
      
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('✅ Connected to live data stream');
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.notifyConnectionStatus('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('🔌 WebSocket connection closed');
        this.connectionState = 'disconnected';
        this.notifyConnectionStatus('disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        this.connectionState = 'error';
        this.notifyConnectionStatus('error');
      };

    } catch (error) {
      console.error('Failed to connect to live data stream:', error);
      this.connectionState = 'error';
      this.notifyConnectionStatus('error');
    }
  }
  // Handle incoming messages
  handleMessage(data) {
    console.log('📨 Received live data:', data);

    switch (data.type) {
      case 'welcome':
        console.log('👋 Welcome message:', data.message);
        break;
      
      case 'live_data':
        this.notifySubscribers('live_data', data);
        break;
      
      case 'continuous_data':
        this.notifySubscribers('continuous_data', data);
        break;
      
      case 'data_update':
        this.notifySubscribers('data_update', data);
        break;
      
      case 'performance_report':
        this.notifySubscribers('performance_report', data.data);
        break;
      
      case 'performance_update':
        this.notifySubscribers('performance_update', data);
        break;
      
      case 'system_alert':
        this.notifySubscribers('system_alert', data);
        break;
      
      case 'subscribed':
        console.log(`✅ Subscribed to ${data.symbol}`);
        break;
      
      case 'unsubscribed':
        console.log(`❌ Unsubscribed from ${data.symbol}`);
        break;
      
      case 'error':
        console.error('WebSocket error:', data.message);
        break;
      
      default:
        console.log('Unknown message type:', data.type);
    }
  }

  // Subscribe to live data updates
  subscribe(type, callback) {
    if (!this.subscribers.has(type)) {
      this.subscribers.set(type, new Set());
    }
    this.subscribers.get(type).add(callback);
    
    console.log(`📡 Subscribed to ${type} updates`);
    
    // Return unsubscribe function
    return () => {
      const callbacks = this.subscribers.get(type);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  // Subscribe to specific symbol updates
  subscribeToSymbol(symbol) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(`subscribe:${symbol.toUpperCase()}`);
    } else {
      console.warn('WebSocket not connected, cannot subscribe to symbol');
    }
  }

  // Unsubscribe from symbol updates
  unsubscribeFromSymbol(symbol) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(`unsubscribe:${symbol.toUpperCase()}`);
    }
  }

  // Get performance report
  getPerformanceReport() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send('get_performance');
    }
  }

  // Get active sessions
  getActiveSessions() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send('list_sessions');
    }
  }

  // Notify all subscribers of a specific type
  notifySubscribers(type, data) {
    const callbacks = this.subscribers.get(type);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${type} callback:`, error);
        }
      });
    }
  }

  // Notify connection status changes
  notifyConnectionStatus(status) {
    this.notifySubscribers('connection_status', { status, timestamp: Date.now() });
  }

  // Attempt to reconnect
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectInterval * this.reconnectAttempts);
    } else {
      console.error('❌ Max reconnection attempts reached');
      this.connectionState = 'failed';
      this.notifyConnectionStatus('failed');
    }
  }

  // Disconnect
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connectionState = 'disconnected';
  }

  // Get connection state
  getConnectionState() {
    return this.connectionState;
  }

  // Check if connected
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
  // HTTP API methods for stealth data
  async startCollectionSession(sessionData) {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/stealth/sessions/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sessionData),
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to start collection session:', error);
      throw error;
    }
  }

  async stopCollectionSession(sessionId) {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/stealth/sessions/${sessionId}/stop`, {
        method: 'POST',
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to stop collection session:', error);
      throw error;
    }
  }

  async getSessionsList() {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/stealth/sessions`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get sessions list:', error);
      throw error;
    }
  }

  async getAgentsList() {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/stealth/agents`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get agents list:', error);
      throw error;
    }
  }

  async getLiveSymbolData(symbol, maxAge = 300) {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/stealth/live/${symbol}?max_age=${maxAge}`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get live symbol data:', error);
      throw error;
    }
  }

  // Continuous Data Service API methods
  async getContinuousStatus() {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/continuous/status`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get continuous status:', error);
      throw error;
    }
  }

  async startContinuousSession(sessionData) {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/continuous/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sessionData),
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to start continuous session:', error);
      throw error;
    }
  }

  async stopContinuousSession(sessionId) {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/continuous/sessions/${sessionId}`, {
        method: 'DELETE',
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to stop continuous session:', error);
      throw error;
    }
  }

  async getContinuousSessionStatus(sessionId) {
    try {
      const response = await fetch(`${this.baseUrl.replace('ws://', 'http://')}/api/continuous/sessions/${sessionId}`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get session status:', error);
      throw error;
    }
  }
}

// Create singleton instance
const liveDataService = new LiveDataService();

export default liveDataService;
