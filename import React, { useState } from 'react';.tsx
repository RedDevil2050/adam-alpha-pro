import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ChakraProvider } from '@chakra-ui/react';
import AnalysisPanel from './components/AnalysisPanel';
import LoginForm from './components/LoginForm';
import { AuthProvider } from './context/AuthContext';

const queryClient = new QueryClient();

const App: React.FC = () => {
  return (
    <ChakraProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <div className="app-container">
            <LoginForm />
            <AnalysisPanel />
          </div>
        </AuthProvider>
      </QueryClientProvider>
    </ChakraProvider>
  );
};

export default App;
