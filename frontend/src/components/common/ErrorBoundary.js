import React from 'react';
import {
  Box,
  Heading,
  Text,
  VStack,
  Button,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  useColorModeValue,
  Code,
  Divider,
  HStack,
  IconButton,
  useDisclosure,
  Collapse
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { RefreshCw, AlertTriangle, ChevronDown, ChevronUp, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const MotionBox = motion(Box);

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null 
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log the error to monitoring service
    if (process.env.NODE_ENV === 'production') {
      console.error('Error Boundary caught an error:', error, errorInfo);
      // You can send this to your error tracking service like Sentry
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return <ErrorFallback 
        error={this.state.error}
        errorInfo={this.state.errorInfo}
        onReload={this.handleReload}
        onReset={this.handleReset}
        fallbackType={this.props.fallbackType || 'full'}
      />;
    }

    return this.props.children;
  }
}

const ErrorFallback = ({ error, errorInfo, onReload, onReset, fallbackType }) => {
  const navigate = useNavigate();
  const { isOpen, onToggle } = useDisclosure();
  
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  if (fallbackType === 'component') {
    return (
      <Alert status="error" borderRadius="md" flexDirection="column" alignItems="start">
        <HStack w="full" justify="space-between">
          <HStack>
            <AlertIcon />
            <AlertTitle>Component Error!</AlertTitle>
          </HStack>
          <Button size="sm" variant="ghost" onClick={onReset}>
            <RefreshCw size={16} />
          </Button>
        </HStack>
        <AlertDescription mt={2}>
          This component encountered an error and couldn't render properly.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Box minH="100vh" bg={bg} p={8}>
      <VStack spacing={8} maxW="600px" mx="auto" pt="10vh">
        <MotionBox
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <VStack spacing={4} textAlign="center">
            <Box
              p={4}
              borderRadius="full"
              bg="red.100"
              color="red.500"
            >
              <AlertTriangle size={48} />
            </Box>
            <Heading size="lg" color="red.500">
              Oops! Something went wrong
            </Heading>
            <Text color="gray.600" fontSize="lg">
              We encountered an unexpected error. Don't worry, our team has been notified.
            </Text>
          </VStack>
        </MotionBox>

        <Alert status="error" borderRadius="lg" p={6}>
          <AlertIcon />
          <Box flex="1">
            <AlertTitle>Error Details</AlertTitle>
            <AlertDescription display="block" mt={2}>
              {error?.message || 'An unknown error occurred'}
            </AlertDescription>
          </Box>
        </Alert>

        <VStack spacing={4} w="full">
          <HStack spacing={4} w="full" justify="center">
            <Button
              leftIcon={<RefreshCw size={16} />}
              colorScheme="brand"
              onClick={onReload}
              size="lg"
            >
              Reload Page
            </Button>
            <Button
              leftIcon={<Home size={16} />}
              variant="outline"
              onClick={() => navigate('/dashboard')}
              size="lg"
            >
              Go Home
            </Button>
          </HStack>

          {error && (
            <Box w="full">
              <Button
                variant="ghost"
                leftIcon={isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                onClick={onToggle}
                size="sm"
              >
                {isOpen ? 'Hide' : 'Show'} Technical Details
              </Button>
              
              <Collapse in={isOpen} animateOpacity>
                <Box
                  mt={4}
                  p={4}
                  bg="gray.50"
                  borderRadius="md"
                  borderWidth="1px"
                  borderColor={borderColor}
                  maxH="300px"
                  overflowY="auto"
                >
                  <VStack spacing={3} align="start">
                    <Box>
                      <Text fontWeight="bold" fontSize="sm" color="gray.700">
                        Error Message:
                      </Text>
                      <Code p={2} display="block" whiteSpace="pre-wrap" fontSize="xs">
                        {error.message}
                      </Code>
                    </Box>
                    
                    <Divider />
                    
                    <Box>
                      <Text fontWeight="bold" fontSize="sm" color="gray.700">
                        Stack Trace:
                      </Text>
                      <Code p={2} display="block" whiteSpace="pre-wrap" fontSize="xs">
                        {error.stack}
                      </Code>
                    </Box>
                    
                    {errorInfo && (
                      <>
                        <Divider />
                        <Box>
                          <Text fontWeight="bold" fontSize="sm" color="gray.700">
                            Component Stack:
                          </Text>
                          <Code p={2} display="block" whiteSpace="pre-wrap" fontSize="xs">
                            {errorInfo.componentStack}
                          </Code>
                        </Box>
                      </>
                    )}
                  </VStack>
                </Box>
              </Collapse>
            </Box>
          )}
        </VStack>

        <Text fontSize="sm" color="gray.500" textAlign="center">
          If this problem persists, please contact our support team with the error details above.
        </Text>
      </VStack>
    </Box>
  );
};

// Hook for functional components
export const useErrorHandler = () => {
  const handleError = (error, errorInfo) => {
    console.error('Component Error:', error, errorInfo);
    // You can send this to your error tracking service
  };

  return handleError;
};

export default ErrorBoundary;
