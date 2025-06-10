import axios from 'axios';

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API Service Class
class ApiService {
  // Authentication
  async login(credentials) {
    const response = await api.post('/api/login', credentials);
    return response.data;
  }

  async verifyToken() {
    const response = await api.get('/api/auth/verify');
    return response.data;
  }

  // Stock Analysis
  async analyzeStock(symbol) {
    const response = await api.get(`/api/analyze/${symbol}`);
    return response.data;
  }

  async analyzeStockEnhanced(symbol, options = {}) {
    const response = await api.post('/api/analyze/enhanced', {
      symbol,
      ...options
    });
    return response.data;
  }

  async validateSymbol(symbol) {
    const response = await api.get(`/api/symbols/validate/${symbol}`);
    return response.data;
  }

  // Market Data
  async getMarketState() {
    const response = await api.get('/api/market-state');
    return response.data;
  }

  async getHealth() {
    const response = await api.get('/api/health');
    return response.data;
  }

  async getMetrics() {
    const response = await api.get('/api/v1/metrics');
    return response.data;
  }

  // Portfolio Management
  async optimizePortfolio(symbols) {
    const response = await api.post('/api/optimize-portfolio', { symbols });
    return response.data;
  }

  // Batch Operations
  async batchAnalyze(symbols) {
    const response = await api.post('/api/batch-analyze', symbols);
    return response.data;
  }

  // Watchlist Management
  async getWatchlist() {
    const response = await api.get('/api/watchlist');
    return response.data;
  }

  async addToWatchlist(symbol) {
    const response = await api.post('/api/watchlist', { symbol });
    return response.data;
  }

  async removeFromWatchlist(symbol) {
    const response = await api.delete(`/api/watchlist/${symbol}`);
    return response.data;
  }

  // Real-time data helpers
  async getStockQuote(symbol) {
    const response = await api.get(`/api/quote/${symbol}`);
    return response.data;
  }

  async getHistoricalData(symbol, period = '1y') {
    const response = await api.get(`/api/historical/${symbol}?period=${period}`);
    return response.data;
  }
}

export default new ApiService();
