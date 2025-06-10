import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Spinner, Center } from '@chakra-ui/react';

// Layout Components
import MainLayout from '../components/layout/MainLayout';
import AuthLayout from '../components/layout/AuthLayout';

// Page Components
import LoginPage from '../pages/LoginPage';
import DashboardPage from '../pages/DashboardPage';
import AnalysisPage from '../pages/AnalysisPage';
import PortfolioPage from '../pages/PortfolioPage';
import WatchlistPage from '../pages/WatchlistPage';
import SettingsPage from '../pages/SettingsPage';
import NotFoundPage from '../pages/NotFoundPage';

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

const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
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
      />

      <Route
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
        path="/settings"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SettingsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Redirect root to dashboard */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 404 Page */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default AppRoutes;
