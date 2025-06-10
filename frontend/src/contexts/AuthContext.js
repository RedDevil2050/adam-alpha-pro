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

  // Set up axios interceptors
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check token validity on app start
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          // Verify token with backend
          const response = await axios.get('/api/auth/verify');
          setUser(response.data.user);
        } catch (error) {
          // Token is invalid
          localStorage.removeItem('token');
          setToken(null);
          toast.error('Session expired. Please login again.');
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [token]);

  const login = async (credentials) => {
    try {
      setLoading(true);
      const response = await axios.post('/api/login', credentials);
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      
      toast.success('Welcome back!');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
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
    isAuthenticated: !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
