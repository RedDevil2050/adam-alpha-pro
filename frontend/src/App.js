import React from 'react';
import { ChakraProvider, extendTheme } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AppRoutes from './routes/AppRoutes';
import { AuthProvider } from './contexts/AuthContext';
import { mode } from '@chakra-ui/theme-tools';

// Custom theme for the market analysis platform
const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#e3f2fd',
      100: '#bbdefb',
      200: '#90caf9',
      300: '#64b5f6',
      400: '#42a5f5',
      500: '#2196f3',
      600: '#1e88e5',
      700: '#1976d2',
      800: '#1565c0',
      900: '#0d47a1',
    },
    success: {
      50: '#e8f5e8',
      500: '#4caf50',
      600: '#43a047',
    },
    danger: {
      50: '#ffebee',
      500: '#f44336',
      600: '#e53935',
    },
  },
  styles: {
    global: (props) => ({
      body: {
        bg: mode('gray.50', 'gray.900')(props),
        color: mode('gray.800', 'gray.100')(props),
      },
    }),
  },
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'brand',
      },
    },
    Card: {
      baseStyle: (props) => ({
        container: {
          bg: mode('white', 'gray.800')(props),
          borderRadius: 'xl',
          boxShadow: mode('lg', 'dark-lg')(props),
          borderWidth: '1px',
          borderColor: mode('gray.200', 'gray.700')(props),
        },
      }),
    },
  },
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Router>
            <div className="App">
              <AppRoutes />
              <Toaster 
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: '#363636',
                    color: '#fff',
                  },
                }}
              />
            </div>
          </Router>
        </AuthProvider>
      </QueryClientProvider>
    </ChakraProvider>
  );
}

export default App;