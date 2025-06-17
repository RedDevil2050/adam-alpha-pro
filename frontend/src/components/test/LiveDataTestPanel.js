import React from 'react';
import { Box, VStack, HStack, Text, Badge, Spinner } from '@chakra-ui/react';
import { useLiveData } from '../../contexts/LiveDataContext';

/**
 * Simple test component to verify live data synchronization
 * This can be added to any page to show live data status
 */
const LiveDataTestPanel = () => {
  const {
    isConnected,
    wsConnected,
    stockData,
    lastUpdate,
    isLoading,
    error,
    connectionStatus,
    hasData
  } = useLiveData();

  return (
    <Box 
      position="fixed" 
      top="20px" 
      right="20px" 
      bg="white" 
      border="2px solid"
      borderColor={wsConnected ? "green.200" : "orange.200"}
      borderRadius="md"
      p={4}
      shadow="lg"
      zIndex={1000}
      minW="250px"
    >
      <VStack align="start" spacing={2}>
        <Text fontWeight="bold" fontSize="sm">Live Data Status</Text>
        
        <HStack>
          <Box
            w={3}
            h={3}
            borderRadius="full"
            bg={isConnected ? 'green.400' : 'red.400'}
            animation={isConnected ? 'pulse 2s infinite' : 'none'}
          />
          <Text fontSize="xs">{connectionStatus}</Text>
        </HStack>

        <HStack>
          <Badge colorScheme={wsConnected ? "green" : "orange"} size="sm">
            {wsConnected ? "WebSocket" : "HTTP"}
          </Badge>
          <Badge colorScheme={hasData ? "blue" : "gray"} size="sm">
            {stockData.length} stocks
          </Badge>
        </HStack>

        {isLoading ? (
          <HStack>
            <Spinner size="xs" />
            <Text fontSize="xs">Loading...</Text>
          </HStack>
        ) : null}

        {error ? (
          <Text fontSize="xs" color="red.500">
            Error: {error}
          </Text>
        ) : null}

        <Text fontSize="xs" color="gray.500">
          Last update: {lastUpdate.toLocaleTimeString()}
        </Text>

        {/* Show first 3 stocks if available */}
        {stockData.slice(0, 3).map((stock) => (
          <HStack key={stock.symbol} fontSize="xs">
            <Text fontWeight="bold">{stock.symbol}:</Text>
            <Text>₹{stock.price}</Text>
            <Text color={stock.change >= 0 ? "green.500" : "red.500"}>
              {stock.change >= 0 ? '+' : ''}{stock.change}%
            </Text>
          </HStack>
        ))}
      </VStack>
    </Box>
  );
};

export default LiveDataTestPanel;
