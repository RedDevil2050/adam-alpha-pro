/**
 * Live Data Context Provider
 * Provides synchronized live data across all components
 */

import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import liveDataService from '../services/liveDataService';
import { useToast } from '@chakra-ui/react';

// Action types
const LIVE_DATA_ACTIONS = {
  SET_CONNECTION_STATUS: 'SET_CONNECTION_STATUS',
  UPDATE_STOCK_DATA: 'UPDATE_STOCK_DATA',
  UPDATE_MARKET_STATE: 'UPDATE_MARKET_STATE',
  SET_LAST_UPDATE: 'SET_LAST_UPDATE',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  BATCH_UPDATE_STOCKS: 'BATCH_UPDATE_STOCKS',
  UPDATE_SINGLE_STOCK: 'UPDATE_SINGLE_STOCK'
};

// Initial state
const initialState = {
  isConnected: false,
  wsConnected: false,
  stockData: [],
  marketState: null,
  lastUpdate: new Date(),
  isLoading: false,
  error: null,
  dataSource: 'HTTP'
};

// Reducer
const liveDataReducer = (state, action) => {
  switch (action.type) {
    case LIVE_DATA_ACTIONS.SET_CONNECTION_STATUS:
      return {
        ...state,
        isConnected: action.payload.isConnected,
        wsConnected: action.payload.wsConnected,
        dataSource: action.payload.dataSource
      };

    case LIVE_DATA_ACTIONS.UPDATE_STOCK_DATA:
      return {
        ...state,
        stockData: action.payload,
        lastUpdate: new Date(),
        isLoading: false,
        error: null
      };

    case LIVE_DATA_ACTIONS.BATCH_UPDATE_STOCKS:
      return {
        ...state,
        stockData: action.payload.stocks,
        lastUpdate: new Date(),
        dataSource: action.payload.source || 'WebSocket'
      };

    case LIVE_DATA_ACTIONS.UPDATE_SINGLE_STOCK:
      return {
        ...state,
        stockData: state.stockData.map(stock =>
          stock.symbol === action.payload.symbol
            ? { ...stock, ...action.payload.data }
            : stock
        ),
        lastUpdate: new Date()
      };

    case LIVE_DATA_ACTIONS.UPDATE_MARKET_STATE:
      return {
        ...state,
        marketState: action.payload,
        lastUpdate: new Date()
      };

    case LIVE_DATA_ACTIONS.SET_LAST_UPDATE:
      return {
        ...state,
        lastUpdate: action.payload
      };

    case LIVE_DATA_ACTIONS.SET_LOADING:
      return {
        ...state,
        isLoading: action.payload
      };

    case LIVE_DATA_ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        isLoading: false
      };

    default:
      return state;
  }
};

// Context
const LiveDataContext = createContext();

// Provider component
export const LiveDataProvider = ({ children }) => {
  const [state, dispatch] = useReducer(liveDataReducer, initialState);
  const toast = useToast();

  // Initialize WebSocket connection
  useEffect(() => {
    const initializeConnection = async () => {
      try {
        dispatch({ type: LIVE_DATA_ACTIONS.SET_LOADING, payload: true });

        // Connect to live data stream
        await liveDataService.connect();

        // Subscribe to connection status
        liveDataService.subscribe('connection', (status) => {
          const isConnected = status === 'connected';
          dispatch({
            type: LIVE_DATA_ACTIONS.SET_CONNECTION_STATUS,
            payload: {
              isConnected,
              wsConnected: isConnected,
              dataSource: isConnected ? 'WebSocket' : 'HTTP'
            }
          });

          if (status === 'connected') {
            toast({
              title: 'Live Data Connected',
              description: 'Real-time data stream is now active across all pages',
              status: 'success',
              duration: 3000,
            });
          } else if (status === 'disconnected') {
            toast({
              title: 'Live Data Disconnected',
              description: 'Attempting to reconnect...',
              status: 'warning',
              duration: 3000,
            });
          }
        });

        // Subscribe to live data updates
        liveDataService.subscribe('live_data', (data) => {
          console.log('🌐 Global: Received live data update:', data);
          
          if (data.data && data.data.stocks) {
            dispatch({
              type: LIVE_DATA_ACTIONS.BATCH_UPDATE_STOCKS,
              payload: { stocks: data.data.stocks, source: 'WebSocket' }
            });
          } else if (data.symbol && data.data) {
            dispatch({
              type: LIVE_DATA_ACTIONS.UPDATE_SINGLE_STOCK,
              payload: { symbol: data.symbol, data: data.data }
            });
          }
        });

        // Subscribe to continuous data updates
        liveDataService.subscribe('continuous_data', (data) => {
          console.log('🌐 Global: Received continuous data update:', data);
          if (data.stocks) {
            dispatch({
              type: LIVE_DATA_ACTIONS.BATCH_UPDATE_STOCKS,
              payload: { stocks: data.stocks, source: 'Continuous' }
            });
          }
        });

        // Subscribe to data updates
        liveDataService.subscribe('data_update', (data) => {
          console.log('🌐 Global: Received data update:', data);
          if (data.data && data.data.stocks) {
            dispatch({
              type: LIVE_DATA_ACTIONS.BATCH_UPDATE_STOCKS,
              payload: { stocks: data.data.stocks, source: 'Update' }
            });
          }
        });

        // Subscribe to major Indian stocks
        const majorStocks = [
          'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR',
          'INFY', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK'
        ];
        
        for (const symbol of majorStocks) {
          await liveDataService.subscribeToSymbol(symbol);
        }

        dispatch({ type: LIVE_DATA_ACTIONS.SET_LOADING, payload: false });

      } catch (error) {
        console.error('Failed to initialize live data connection:', error);
        dispatch({ type: LIVE_DATA_ACTIONS.SET_ERROR, payload: error.message });
        dispatch({
          type: LIVE_DATA_ACTIONS.SET_CONNECTION_STATUS,
          payload: {
            isConnected: false,
            wsConnected: false,
            dataSource: 'HTTP'
          }
        });
      }
    };

    initializeConnection();

    // Cleanup on unmount
    return () => {
      liveDataService.disconnect();
    };
  }, [toast]);

  // Actions
  const updateStockData = useCallback((stocks) => {
    dispatch({ type: LIVE_DATA_ACTIONS.UPDATE_STOCK_DATA, payload: stocks });
  }, []);

  const updateMarketState = useCallback((market) => {
    dispatch({ type: LIVE_DATA_ACTIONS.UPDATE_MARKET_STATE, payload: market });
  }, []);

  const subscribeToSymbol = useCallback(async (symbol) => {
    try {
      await liveDataService.subscribeToSymbol(symbol);
    } catch (error) {
      console.error(`Failed to subscribe to ${symbol}:`, error);
    }
  }, []);

  const unsubscribeFromSymbol = useCallback(async (symbol) => {
    try {
      await liveDataService.unsubscribeFromSymbol(symbol);
    } catch (error) {
      console.error(`Failed to unsubscribe from ${symbol}:`, error);
    }
  }, []);

  const value = {
    // State
    ...state,
    
    // Actions
    updateStockData,
    updateMarketState,
    subscribeToSymbol,
    unsubscribeFromSymbol,
    
    // Derived state
    hasData: state.stockData.length > 0,
    connectionStatus: state.wsConnected ? 'WebSocket' : state.isConnected ? 'HTTP' : 'Disconnected'
  };

  return <LiveDataContext.Provider value={value}>{children}</LiveDataContext.Provider>;
};

// Hook
export const useLiveData = () => {
  const context = useContext(LiveDataContext);
  if (context === undefined) {
    throw new Error('useLiveData must be used within a LiveDataProvider');
  }
  return context;
};

export default LiveDataContext;
