/**
 * Live Data Ticker Component
 * Shows synchronized live stock data across all pages
 */

import React from 'react';
import {
  Box,
  HStack,
  Text,
  Badge,
  Skeleton,
  useColorModeValue
} from '@chakra-ui/react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { useLiveData } from '../../contexts/LiveDataContext';

const LiveDataTicker = ({ symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK'], maxItems = 4 }) => {
  const { stockData, isConnected, wsConnected, lastUpdate } = useLiveData();
  
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  // Filter and limit the stocks to display
  const displayStocks = stockData
    .filter(stock => symbols.includes(stock.symbol))
    .slice(0, maxItems);

  if (!isConnected || displayStocks.length === 0) {
    return (
      <Box
        bg={bg}
        border="1px"
        borderColor={borderColor}
        borderRadius="md"
        p={3}
        overflow="hidden"
      >
        <HStack spacing={4}>
          {[...Array(maxItems)].map((_, index) => (
            <Skeleton key={index} height="20px" width="120px" />
          ))}
        </HStack>
      </Box>
    );
  }

  return (
    <Box
      bg={bg}
      border="1px"
      borderColor={borderColor}
      borderRadius="md"
      p={3}
      overflow="hidden"
      position="relative"
    >
      {/* Live indicator */}
      <Badge
        position="absolute"
        top={1}
        right={1}
        colorScheme={wsConnected ? "green" : "blue"}
        variant="subtle"
        fontSize="xs"
      >
        {wsConnected ? "LIVE" : "HTTP"}
      </Badge>

      <HStack spacing={6} animate={{ x: [0, -100] }} transition={{ duration: 20, repeat: Infinity }}>
        {displayStocks.map((stock) => {
          const isPositive = (stock.change || stock.changePercent || 0) > 0;
          const changePercent = stock.change_percent || stock.changePercent || 0;
          
          return (
            <HStack key={stock.symbol} spacing={2} minW="fit-content">
              <Text fontWeight="bold" fontSize="sm">
                {stock.symbol}
              </Text>
              <Text fontSize="sm">
                ₹{stock.price?.toFixed(2) || 'N/A'}
              </Text>
              <HStack spacing={1}>
                {isPositive ? (
                  <TrendingUp size={12} color="#38A169" />
                ) : (
                  <TrendingDown size={12} color="#E53E3E" />
                )}
                <Text
                  fontSize="xs"
                  color={isPositive ? "green.500" : "red.500"}
                  fontWeight="medium"
                >
                  {changePercent > 0 ? '+' : ''}{changePercent.toFixed(2)}%
                </Text>
              </HStack>
            </HStack>
          );
        })}
      </HStack>

      {/* Last update indicator */}
      <Text
        position="absolute"
        bottom={1}
        left={2}
        fontSize="xs"
        color="gray.500"
      >
        Updated: {lastUpdate.toLocaleTimeString()}
      </Text>
    </Box>
  );
};

export default LiveDataTicker;
