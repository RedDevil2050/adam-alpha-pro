/**
 * Live Data Card Component
 * Displays live data for a single stock with real-time updates
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  CardHeader,
  CardBody,
  HStack,
  VStack,
  Text,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Skeleton,
  useColorModeValue,
  Box
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, TrendingDown } from 'lucide-react';
import { useLiveData } from '../../contexts/LiveDataContext';

const MotionCard = motion(Card);

const LiveDataCard = ({ symbol, showDetails = true }) => {
  const { stockData, subscribeToSymbol, unsubscribeFromSymbol, wsConnected, lastUpdate } = useLiveData();
  const [isHighlighted, setIsHighlighted] = useState(false);
  
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const highlightColor = useColorModeValue('blue.50', 'blue.900');
  
  // Find the stock data for this symbol
  const stockInfo = stockData.find(stock => stock.symbol === symbol);
  
  // Subscribe to this symbol when component mounts
  useEffect(() => {
    subscribeToSymbol(symbol);
    return () => unsubscribeFromSymbol(symbol);
  }, [symbol, subscribeToSymbol, unsubscribeFromSymbol]);

  // Highlight card when data updates
  useEffect(() => {
    if (stockInfo) {
      setIsHighlighted(true);
      const timer = setTimeout(() => setIsHighlighted(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [stockInfo?.price, stockInfo?.lastUpdate]);

  if (!stockInfo) {
    return (
      <Card bg={bg} border="1px" borderColor={borderColor}>
        <CardHeader pb={2}>
          <HStack justify="space-between">
            <Skeleton height="20px" width="80px" />
            <Skeleton height="16px" width="40px" />
          </HStack>
        </CardHeader>
        <CardBody pt={0}>
          <VStack align="start" spacing={2}>
            <Skeleton height="24px" width="100px" />
            <Skeleton height="16px" width="60px" />
          </VStack>
        </CardBody>
      </Card>
    );
  }

  const isPositive = (stockInfo.change || stockInfo.changePercent || 0) > 0;
  const changePercent = stockInfo.change_percent || stockInfo.changePercent || 0;
  const change = stockInfo.change || 0;

  return (
    <MotionCard
      bg={isHighlighted ? highlightColor : bg}
      border="1px"
      borderColor={isHighlighted ? 'blue.300' : borderColor}
      transition={{
        background: { duration: 0.3 },
        borderColor: { duration: 0.3 }
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <CardHeader pb={2}>
        <HStack justify="space-between" align="center">
          <HStack spacing={2}>
            <Text fontWeight="bold" fontSize="lg">
              {stockInfo.symbol}
            </Text>
            <Badge
              colorScheme={wsConnected ? "green" : "blue"}
              variant="subtle"
              fontSize="xs"
            >
              {wsConnected ? "LIVE" : "HTTP"}
            </Badge>
          </HStack>
          
          {isPositive ? (
            <TrendingUp size={16} color="#38A169" />
          ) : (
            <TrendingDown size={16} color="#E53E3E" />
          )}
        </HStack>
        
        {stockInfo.name && (
          <Text fontSize="sm" color="gray.600" noOfLines={1}>
            {stockInfo.name}
          </Text>
        )}
      </CardHeader>
      
      <CardBody pt={0}>
        <VStack align="start" spacing={3}>
          {/* Price */}
          <Stat>
            <StatLabel fontSize="sm">Current Price</StatLabel>
            <StatNumber fontSize="2xl">
              ₹{stockInfo.price?.toFixed(2) || 'N/A'}
            </StatNumber>
            <StatHelpText mb={0}>
              <HStack spacing={1}>
                <StatArrow type={isPositive ? 'increase' : 'decrease'} />
                <Text>
                  {change > 0 ? '+' : ''}₹{change.toFixed(2)} ({changePercent > 0 ? '+' : ''}{changePercent.toFixed(2)}%)
                </Text>
              </HStack>
            </StatHelpText>
          </Stat>

          {showDetails && (
            <VStack align="start" spacing={1} width="100%">
              {/* Volume */}
              {stockInfo.volume && (
                <HStack justify="space-between" width="100%">
                  <Text fontSize="sm" color="gray.600">Volume:</Text>
                  <Text fontSize="sm">{stockInfo.volume.toLocaleString()}</Text>
                </HStack>
              )}
              
              {/* Last Updated */}
              <HStack justify="space-between" width="100%">
                <Text fontSize="xs" color="gray.500">Updated:</Text>
                <Text fontSize="xs" color="gray.500">
                  {lastUpdate.toLocaleTimeString()}
                </Text>
              </HStack>
            </VStack>
          )}
        </VStack>
      </CardBody>
      
      {/* Live pulse animation */}
      {isHighlighted && (
        <Box
          position="absolute"
          top="50%"
          right="10px"
          transform="translateY(-50%)"
        >
          <motion.div
            animate={{
              scale: [1, 1.5, 1],
              opacity: [0.7, 0, 0.7]
            }}
            transition={{
              duration: 1,
              repeat: 2
            }}
          >
            <Activity size={12} color="#3182CE" />
          </motion.div>
        </Box>
      )}
    </MotionCard>
  );
};

export default LiveDataCard;
