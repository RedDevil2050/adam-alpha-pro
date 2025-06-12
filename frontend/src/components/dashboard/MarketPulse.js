import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  useColorModeValue,
  Card,
  CardBody,
  Progress,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, Zap } from 'lucide-react';

const MotionCard = motion(Card);

const MarketPulse = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const pulseData = [
    {
      symbol: 'NIFTY 50',
      value: '19,674.25',
      change: -63.45,
      changePercent: -0.32,
      volume: '2.5B',
      trend: 'down'
    },
    {
      symbol: 'SENSEX',
      value: '66,023.16',
      change: -185.23,
      changePercent: -0.28,
      volume: '1.8B',
      trend: 'down'
    },
    {
      symbol: 'BANK NIFTY',
      value: '44,567.80',
      change: 234.56,
      changePercent: 0.53,
      volume: '876M',
      trend: 'up'
    },
    {
      symbol: 'NIFTY IT',
      value: '31,245.60',
      change: 567.89,
      changePercent: 1.85,
      volume: '234M',
      trend: 'up'
    }
  ];

  return (
    <MotionCard
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      bg={cardBg}
      borderColor={borderColor}
      borderWidth="1px"
    >
      <CardBody>
        <VStack spacing={4} align="stretch">
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <Box
                p={2}
                borderRadius="lg"
                bg="purple.100"
                color="purple.600"
              >
                <Activity size={20} />
              </Box>
              <VStack align="start" spacing={0}>
                <Text fontWeight="bold" fontSize="lg">
                  Market Pulse
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Live market sentiment
                </Text>
              </VStack>
            </HStack>
            <Badge colorScheme="green" variant="outline">
              <HStack spacing={1}>
                <Zap size={12} />
                <Text>LIVE</Text>
              </HStack>
            </Badge>
          </HStack>

          {/* Market Indices */}
          <VStack spacing={3} align="stretch">
            {pulseData.map((market, index) => (
              <motion.div
                key={market.symbol}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Box
                  p={4}
                  borderRadius="lg"
                  bg={useColorModeValue('gray.50', 'gray.700')}
                  border="1px"
                  borderColor={useColorModeValue('gray.200', 'gray.600')}
                  _hover={{
                    borderColor: market.trend === 'up' ? 'green.300' : 'red.300',
                    transform: 'translateY(-1px)',
                    boxShadow: 'md'
                  }}
                  transition="all 0.2s"
                  cursor="pointer"
                >
                  <Flex justify="space-between" align="center">
                    <VStack align="start" spacing={1}>
                      <Text fontWeight="bold" fontSize="sm">
                        {market.symbol}
                      </Text>
                      <Text fontSize="lg" fontWeight="bold">
                        {market.value}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        Vol: {market.volume}
                      </Text>
                    </VStack>

                    <VStack align="end" spacing={1}>
                      <HStack>
                        {market.trend === 'up' ? (
                          <TrendingUp size={16} color="#38A169" />
                        ) : (
                          <TrendingDown size={16} color="#E53E3E" />
                        )}
                        <Text
                          color={market.trend === 'up' ? 'green.500' : 'red.500'}
                          fontWeight="medium"
                          fontSize="sm"
                        >
                          {market.change > 0 ? '+' : ''}{market.change.toFixed(2)}
                        </Text>
                      </HStack>
                      <Badge
                        colorScheme={market.trend === 'up' ? 'green' : 'red'}
                        variant="subtle"
                      >
                        {market.changePercent > 0 ? '+' : ''}{market.changePercent.toFixed(2)}%
                      </Badge>
                    </VStack>
                  </Flex>

                  {/* Mini progress bar for visual appeal */}
                  <Box mt={2}>
                    <Progress
                      value={Math.abs(market.changePercent) * 20}
                      colorScheme={market.trend === 'up' ? 'green' : 'red'}
                      size="xs"
                      borderRadius="full"
                    />
                  </Box>
                </Box>
              </motion.div>
            ))}
          </VStack>

          {/* Market Status */}
          <Box
            p={3}
            borderRadius="md"
            bg={useColorModeValue('blue.50', 'blue.900')}
            border="1px"
            borderColor="blue.200"
            textAlign="center"
          >
            <HStack justify="center" spacing={2}>
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Box w={2} h={2} bg="green.500" borderRadius="full" />
              </motion.div>
              <Text fontSize="sm" fontWeight="medium" color="blue.700">
                Markets are OPEN
              </Text>
              <Text fontSize="xs" color="blue.600">
                • Next update in 5s
              </Text>
            </HStack>
          </Box>
        </VStack>
      </CardBody>
    </MotionCard>
  );
};

export default MarketPulse;
