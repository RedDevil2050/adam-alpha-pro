import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Spinner, Center } from '@chakra-ui/react';

// Layout Components
import MainLayout from '../components/layout/MainLayout';
import AuthLayout from '../components/layout/AuthLayout';

// Page Components
import LoginPage from '../pages/LoginPage';
import LandingPage from '../pages/LandingPage';
import DashboardPage from '../pages/DashboardPage';
import AnalysisPage from '../pages/AnalysisPage';
import PortfolioPage from '../pages/PortfolioPage';
import WatchlistPage from '../pages/WatchlistPage';
import SettingsPage from '../pages/SettingsPage';
import NotFoundPage from '../pages/NotFoundPage';

// Indian Stock Components
import IndianStockScreener from '../components/screener/IndianStockScreener';
import StockDetailPage from '../components/stocks/StockDetailPage';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" thickness="4px" />
      </Center>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Public Route Component (redirects to dashboard if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" thickness="4px" />
      </Center>
    );
  }

  return !isAuthenticated ? children : <Navigate to="/dashboard" replace />;
};

// Root Route Component (handles authentication-based redirects)
const RootRoute = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" thickness="4px" />
      </Center>
    );
  }

  return isAuthenticated ? 
    <Navigate to="/dashboard" replace /> : 
    <Navigate to="/landing" replace />;
};

const AppRoutes = () => {
  return (    <Routes>
      {/* Public Routes */}
      <Route
        path="/landing"
        element={
          <PublicRoute>
            <LandingPage />
          </PublicRoute>
        }
      />
      
      <Route
        path="/login"
        element={
          <PublicRoute>
            <AuthLayout>
              <LoginPage />
            </AuthLayout>
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <MainLayout>
              <DashboardPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/analysis"
        element={
          <ProtectedRoute>
            <MainLayout>
              <AnalysisPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/analysis/:symbol"
        element={
          <ProtectedRoute>
            <MainLayout>
              <AnalysisPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/portfolio"
        element={
          <ProtectedRoute>
            <MainLayout>
              <PortfolioPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />      <Route
        path="/watchlist"
        element={
          <ProtectedRoute>
            <MainLayout>
              <WatchlistPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/screener"
        element={
          <ProtectedRoute>
            <MainLayout>
              <IndianStockScreener />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/stock/:symbol"
        element={
          <ProtectedRoute>
            <MainLayout>
              <StockDetailPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SettingsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Redirect root based on authentication */}
      <Route path="/" element={<RootRoute />} />

      {/* 404 Page */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default AppRoutes;
