import axios from 'axios';

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      // Only send real tokens to backend, not demo tokens
      if (!token.startsWith('demo-token-')) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    // For testing purposes, add a test header
    config.headers['X-Test-Mode'] = 'true';
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const token = localStorage.getItem('token');
    // For testing, don't redirect on 401 for certain endpoints or demo tokens
    if (error.response?.status === 401 && !error.config?.url?.includes('/symbols/validate') && !token?.startsWith('demo-token-')) {
      localStorage.removeItem('token');
      // window.location.href = '/login'; // Commented out for testing
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
    try {
      const response = await api.get(`/api/analyze/${symbol}`);
      return response.data;
    } catch (error) {
      console.warn('Backend analysis failed, providing demo data:', error.message);
      // Return demo analysis data for Indian stocks
      return this.getDemoAnalysisData(symbol);
    }
  }
  async analyzeStockEnhanced(symbol, options = {}) {
    try {
      const response = await api.get(`/api/analyze/enhanced/${symbol}`, { params: options });
      return response.data;
    } catch (error) {
      console.warn('Backend enhanced analysis failed, providing demo data:', error.message);
      return this.getDemoEnhancedAnalysisData(symbol);
    }
  }

  async validateSymbol(symbol) {
    try {
      const response = await api.get(`/api/symbols/validate/${symbol}`);
      return response.data;
    } catch (error) {
      console.warn(`Symbol validation failed for ${symbol}:`, error.message);
      // Return fallback validation for Indian stocks
      return {
        symbol: symbol,
        is_valid: true,
        is_indian_symbol: true,
        detected_exchange: 'NSE',
        base_symbol: symbol.replace(/\.(NS|BO)$/, ''),
        provider_formats: {
          yahoo_finance: symbol.includes('.') ? symbol : `${symbol}.NS`,
          alpha_vantage: symbol.replace(/\.(NS|BO)$/, ''),
          polygon: `NSE:${symbol.replace(/\.(NS|BO)$/, '')}`,
          finnhub: symbol.replace(/\.(NS|BO)$/, '')
        }
      };
    }
  }

  // Test backend connectivity
  async testBackendConnection() {
    try {
      const response = await api.get('/api/health');
      return { success: true, data: response.data };
    } catch (error) {
      console.warn('Backend connection test failed:', error.message);
      return { success: false, error: error.message };
    }
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
  }  // Real-time data helpers
  async getStockQuote(symbol) {
    try {
      const response = await api.get(`/api/analyze/${symbol}`);
      return response.data;
    } catch (error) {
      console.warn('Live quote failed, using fallback:', error.message);
      return this.getDemoQuoteData(symbol);
    }
  }
  async getHistoricalData(symbol, period = '1y') {
    try {
      const response = await api.get(`/api/historical/${symbol}?period=${period}`);
      return response.data;
    } catch (error) {
      console.warn('Historical data failed, using fallback:', error.message);
      return this.getDemoHistoricalData(symbol, period);
    }
  }
  // Live market data methods
  async getLiveMarketStatus() {
    try {
      const response = await api.get('/api/market-state');
      return response.data;
    } catch (error) {
      console.warn('Live market status failed, using fallback:', error.message);
      return {
        status: 'success',
        market_status: 'UNKNOWN',
        timestamp: new Date().toISOString()
      };
    }
  }
  async getLiveIndianIndices() {
    try {
      const response = await api.get('/api/market-state');
      // Extract indices from market state data
      if (response.data && response.data.data && response.data.data.indices) {
        return {
          status: 'success',
          data: response.data.data.indices,
          timestamp: response.data.data.timestamp
        };
      }
      return response.data;
    } catch (error) {
      console.warn('Live indices failed, using fallback:', error.message);
      return this.getIndianMarketIndices();
    }
  }
  async getLiveIndianStocks() {
    try {
      const response = await api.get('/api/live-data');
      return response.data;
    } catch (error) {
      console.warn('Live stocks failed, using fallback:', error.message);
      return this.getIndianStockList();
    }
  }
  // Indian Stock Specific APIs
  async getIndianStockList() {
    try {
      // Try to get live data from backend first
      const liveResponse = await api.get('/api/live-data');
      if (liveResponse.data && liveResponse.data.data && liveResponse.data.data.stocks) {
        return {
          stocks: liveResponse.data.data.stocks,
          source: 'live',
          timestamp: liveResponse.data.data.timestamp || liveResponse.data.timestamp
        };
      }
    } catch (error) {
      console.warn('Live stock data not available, trying regular API:', error.message);
    }

    try {
      // Fallback to regular API
      const response = await api.get('/api/indian-stocks');
      return response.data;
    } catch (error) {
      console.warn('Backend not available, using fallback data:', error.message);
      // Return extensive mock data that matches Trendlyne format
      return {
        stocks: [
          {
            symbol: 'RELIANCE',
            name: 'Reliance Industries Ltd',
            sector: 'Oil & Gas',
            price: 2456.75,
            change: 45.30,
            changePercent: 1.87,
            volume: 3456789,
            marketCap: 16.6e12,
            peRatio: 25.4,
            pbRatio: 1.8,
            divYield: 0.35,
            roe: 14.2,
            debt_equity: 0.42,
            eps: 96.8,
            bookValue: 1367.5,
            intrinsicValue: 2650,
            trendScore: 85,
            qualityScore: 92,
            momentumScore: 78,
            valueScore: 82,
            technicalRating: 'Strong Buy',
            fundamentalRating: 'Buy',
            analystRating: 'Buy',
            priceTarget: 2750,
            support: 2400,
            resistance: 2550,
            weekHigh52: 2968,
            weekLow52: 2173,
            avgVolume: 2890000,
            fiiHolding: 24.8,
            diiHolding: 14.2,
            promoterHolding: 50.3,
            retailHolding: 10.7
          },
          {
            symbol: 'TCS',
            name: 'Tata Consultancy Services Ltd',
            sector: 'IT Services',
            price: 3567.20,
            change: -23.45,
            changePercent: -0.65,
            volume: 2345678,
            marketCap: 13.0e12,
            peRatio: 28.9,
            pbRatio: 12.5,
            divYield: 1.25,
            roe: 44.2,
            debt_equity: 0.05,
            eps: 123.5,
            bookValue: 285.4,
            intrinsicValue: 3800,
            trendScore: 72,
            qualityScore: 96,
            momentumScore: 65,
            valueScore: 75,
            technicalRating: 'Hold',
            fundamentalRating: 'Strong Buy',
            analystRating: 'Buy',
            priceTarget: 3850,
            support: 3450,
            resistance: 3650,
            weekHigh52: 4259,
            weekLow52: 3056,
            avgVolume: 1890000,
            fiiHolding: 45.2,
            diiHolding: 8.5,
            promoterHolding: 72.0,
            retailHolding: 14.3
          },
          {
            symbol: 'HDFCBANK',
            name: 'HDFC Bank Ltd',
            sector: 'Banking',
            price: 1634.80,
            change: 18.75,
            changePercent: 1.16,
            volume: 4567890,
            marketCap: 12.4e12,
            peRatio: 19.2,
            pbRatio: 2.8,
            divYield: 1.1,
            roe: 17.8,
            debt_equity: 0.0,
            eps: 85.2,
            bookValue: 584.3,
            intrinsicValue: 1750,
            trendScore: 88,
            qualityScore: 94,
            momentumScore: 82,
            valueScore: 78,
            technicalRating: 'Buy',
            fundamentalRating: 'Strong Buy',
            analystRating: 'Buy',
            priceTarget: 1800,
            support: 1580,
            resistance: 1680,
            weekHigh52: 1794,
            weekLow52: 1363,
            avgVolume: 3450000,
            fiiHolding: 55.8,
            diiHolding: 12.4,
            promoterHolding: 0.0,
            retailHolding: 31.8
          },
          {
            symbol: 'INFY',
            name: 'Infosys Ltd',
            sector: 'IT Services',
            price: 1567.45,
            change: 12.35,
            changePercent: 0.79,
            volume: 3789012,
            marketCap: 6.5e12,
            peRatio: 24.6,
            pbRatio: 8.9,
            divYield: 2.8,
            roe: 31.5,
            debt_equity: 0.08,
            eps: 63.7,
            bookValue: 176.2,
            intrinsicValue: 1650,
            trendScore: 75,
            qualityScore: 90,
            momentumScore: 71,
            valueScore: 80,
            technicalRating: 'Buy',
            fundamentalRating: 'Buy',
            analystRating: 'Buy',
            priceTarget: 1720,
            support: 1520,
            resistance: 1620,
            weekHigh52: 1884,
            weekLow52: 1351,
            avgVolume: 2980000,
            fiiHolding: 35.2,
            diiHolding: 15.8,
            promoterHolding: 13.0,
            retailHolding: 36.0
          },
          {
            symbol: 'ICICIBANK',
            name: 'ICICI Bank Ltd',
            sector: 'Banking',
            price: 1078.30,
            change: -8.90,
            changePercent: -0.82,
            volume: 5678901,
            marketCap: 7.6e12,
            peRatio: 18.5,
            pbRatio: 2.4,
            divYield: 0.85,
            roe: 15.2,
            debt_equity: 0.0,
            eps: 58.3,
            bookValue: 449.2,
            intrinsicValue: 1150,
            trendScore: 68,
            qualityScore: 88,
            momentumScore: 64,
            valueScore: 85,
            technicalRating: 'Hold',
            fundamentalRating: 'Buy',
            analystRating: 'Buy',
            priceTarget: 1200,
            support: 1040,
            resistance: 1120,
            weekHigh52: 1257,
            weekLow52: 854,
            avgVolume: 4230000,
            fiiHolding: 48.6,
            diiHolding: 18.2,
            promoterHolding: 0.0,
            retailHolding: 33.2
          }
        ]
      };
    }
  }
  async getIndianMarketIndices() {
    try {
      // Try to get data from backend first
      const response = await api.get('/api/indian-indices');
      return response.data;
    } catch (error) {
      console.warn('Backend not available for indices, using fallback data:', error.message);
      return {
        indices: [
          {
            name: 'Nifty 50',
            symbol: '^NSEI',
            value: 19674.25,
            change: 156.35,
            changePercent: 0.80,
            volume: 245678900,
            high: 19798.50,
            low: 19567.80
          },
          {
            name: 'Sensex',
            symbol: '^BSESN',
            value: 65953.48,
            change: 234.12,
            changePercent: 0.36,
            volume: 156789000,
            high: 66125.30,
            low: 65789.20
          },
          {
            name: 'Bank Nifty',
            symbol: '^NSEBANK',
            value: 44287.35,
            change: -89.75,
            changePercent: -0.20,
            volume: 98765400,
            high: 44456.80,
            low: 44123.50
          },
          {
            name: 'Nifty IT',
            symbol: '^NSEIT',
            value: 28456.80,
            change: 245.60,
            changePercent: 0.87,
            volume: 45678900,
            high: 28567.90,
            low: 28234.10
          }
        ]
      };
    }
  }

  async getIndianStockDetail(symbol) {
    // Validate symbol first
    const validation = await this.validateSymbol(symbol);
    if (!validation.is_valid) {
      throw new Error(`Invalid symbol: ${symbol}`);
    }

    // For now, return mock detailed data
    return {
      symbol: symbol,
      name: `${symbol} Company Limited`,
      sector: 'Technology',
      industry: 'Software Services',
      exchange: 'NSE',
      price: 1234.56,
      change: 12.34,
      changePercent: 1.01,
      volume: 1000000,
      marketCap: 5e12,
      peRatio: 25.4,
      pbRatio: 3.2,
      roe: 18.5,
      validation: validation
    };
  }

  async screenIndianStocks(filters = {}) {
    // This would typically filter from backend database
    const stocks = await this.getIndianStockList();
    
    // Apply filters (basic implementation)
    let filteredStocks = stocks.stocks;
    
    if (filters.sector && filters.sector !== 'all') {
      filteredStocks = filteredStocks.filter(stock => stock.sector === filters.sector);
    }
    
    if (filters.minPrice) {
      filteredStocks = filteredStocks.filter(stock => stock.price >= filters.minPrice);
    }
    
    if (filters.maxPrice) {
      filteredStocks = filteredStocks.filter(stock => stock.price <= filters.maxPrice);
    }    
    return { stocks: filteredStocks };
  }

  // Demo data methods for fallback when backend is unavailable
  getDemoAnalysisData(symbol) {
    return {
      symbol: symbol,
      name: `${symbol} Limited`,
      current_price: 1234.56,
      price_change: 12.34,
      price_change_percent: 1.01,
      volume: 1000000,
      market_cap: 500000000000,
      pe_ratio: 25.4,
      pb_ratio: 3.2,
      roe: 18.5,
      sector: 'Technology',
      exchange: 'NSE',
      analysis: {
        technical: {
          signal: 'BUY',
          confidence: 75,
          indicators: {
            rsi: 45.2,
            macd: 'BULLISH',
            moving_averages: 'ABOVE'
          }
        },
        fundamental: {
          rating: 4,
          financial_health: 'STRONG',
          growth_potential: 'HIGH'
        }
      }
    };
  }

  getDemoEnhancedAnalysisData(symbol) {
    return {
      ...this.getDemoAnalysisData(symbol),
      enhanced_metrics: {
        quality_score: 85,
        momentum_score: 70,
        value_score: 60,
        growth_score: 80,
        ownership: {
          fii_holding: 15.5,
          dii_holding: 25.3,
          retail_holding: 59.2
        },
        financials: {
          revenue_growth: 12.5,
          profit_margin: 18.2,
          debt_to_equity: 0.45,
          return_on_assets: 8.9
        }
      }
    };
  }

  getDemoQuoteData(symbol) {
    return {
      symbol: symbol,
      name: `${symbol} Limited`,
      price: 1234.56,
      change: 12.34,
      changePercent: 1.01,
      volume: 1000000,
      marketCap: 5e12,
      high: 1250.00,
      low: 1220.00,
      open: 1225.00,
      previousClose: 1222.22,
      timestamp: new Date().toISOString(),
      source: 'demo'
    };
  }

  getDemoHistoricalData(symbol, period) {
    const basePrice = 1000;
    const days = period === '1y' ? 365 : period === '6m' ? 180 : period === '3m' ? 90 : 30;
    const data = [];
    
    for (let i = days; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const variation = (Math.random() - 0.5) * 100;
      data.push({
        date: date.toISOString().split('T')[0],
        price: basePrice + variation,
        volume: Math.floor(1000000 + Math.random() * 500000)
      });
    }
    
    return {
      symbol: symbol,
      period: period,
      data: data,
      source: 'demo'
    };
  }
}

export default new ApiService();
