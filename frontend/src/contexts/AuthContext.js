import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Set up axios interceptors - only for real tokens, not demo tokens
  useEffect(() => {
    if (token && !token.startsWith('demo-token-')) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);  // Check token validity on app start or when token changes
  useEffect(() => {
    const initAuth = async () => {
      console.log('🔍 Initializing auth, token:', token ? token.substring(0, 20) + '...' : 'none');
      
      if (token) {
        try {
          // Handle demo token differently
          if (token.startsWith('demo-token-')) {
            console.log('✅ Demo token detected, setting demo user');
            // For demo tokens, just set a demo user without backend verification
            const demoUser = {
              id: 'demo-user',
              username: 'demo',
              email: 'demo@indianstocks.com',
              name: 'Demo User',
              role: 'user'
            };
            setUser(demoUser);
            console.log('✅ Demo user set successfully');
          } else {
            console.log('🌐 Real token detected, verifying with backend...');
            try {
              // Verify real token with backend
              const response = await axios.get('/api/auth/verify');
              setUser(response.data.user);
              console.log('✅ Real user verified successfully');
            } catch (backendError) {
              console.warn('⚠️ Backend verification failed, treating as demo mode');
              // If backend is unavailable, treat as demo for development
              const demoUser = {
                id: 'demo-user',
                username: 'demo',
                email: 'demo@indianstocks.com',
                name: 'Demo User',
                role: 'user'
              };
              setUser(demoUser);
            }
          }
        } catch (error) {
          console.error('❌ Token verification failed:', error.message);
          // Token is invalid - only clear if it's not a demo token
          if (!token.startsWith('demo-token-')) {
            console.log('🗑️ Clearing invalid real token');
            localStorage.removeItem('token');
            setToken(null);
            setUser(null);
            toast.error('Session expired. Please login again.');
          } else {
            console.log('🔧 Demo token error, continuing with demo user anyway');
            // For demo token errors, just continue with demo user
            const demoUser = {
              id: 'demo-user',
              username: 'demo',
              email: 'demo@indianstocks.com',
              name: 'Demo User',
              role: 'user'
            };
            setUser(demoUser);
          }
        }
      } else {
        console.log('ℹ️ No token found, user not logged in');
        setUser(null);
      }
      setLoading(false);
      console.log('✅ Auth initialization complete');
    };

    initAuth();
  }, [token]);const login = async (credentials) => {
    try {
      setLoading(true);
      
      console.log('🔐 Login attempt:', credentials.username);
      
      // Demo/Testing mode for Indian Stock Platform
      if (credentials.username === 'demo' && credentials.password === 'demo') {
        const demoToken = 'demo-token-indian-stocks-' + Date.now();
        const demoUser = {
          id: 'demo-user',
          username: 'demo',
          email: 'demo@indianstocks.com',
          name: 'Demo User',
          role: 'user'
        };
        
        console.log('✅ Demo login successful, setting token:', demoToken);
        
        localStorage.setItem('token', demoToken);
        setToken(demoToken);
        setUser(demoUser);
        
        toast.success('Welcome to Indian Stock Analysis Platform!');
        return { success: true };
      }
      
      // Regular authentication
      console.log('🌐 Attempting regular authentication...');
      const response = await axios.post('/api/login', credentials);
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      
      toast.success('Welcome back!');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed. Try demo/demo for testing.';
      console.error('❌ Login failed:', message);
      toast.error(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
    toast.success('Logged out successfully');
  };
  const value = {
    user,
    token,
    loading,
    login,
    logout,
    isAuthenticated: !!token && !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
