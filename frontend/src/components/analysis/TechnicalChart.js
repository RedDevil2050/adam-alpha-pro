import React from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  useColorModeValue,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

const MotionCard = motion(Card);

const TechnicalChart = ({ technicalData }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  if (!technicalData) {
    return (
      <Card bg={bgColor} borderColor={borderColor} borderWidth="1px">
        <CardBody>
          <Text color="gray.500">No technical analysis data available</Text>
        </CardBody>
      </Card>
    );
  }

  const getIndicatorColor = (value, type) => {
    if (type === 'rsi') {
      if (value > 70) return 'red';
      if (value < 30) return 'green';
      return 'blue';
    }
    if (type === 'macd') {
      return value > 0 ? 'green' : 'red';
    }
    return 'blue';
  };

  const formatValue = (value, decimals = 2) => {
    if (typeof value === 'number') {
      return value.toFixed(decimals);
    }
    return value;
  };

  return (
    <MotionCard
      bg={bgColor}
      borderColor={borderColor}
      borderWidth="1px"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <CardHeader>
        <Heading size="md">Technical Analysis</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={6} align="stretch">
          {/* Price Action */}
          <Box>
            <Text fontWeight="semibold" mb={3}>Price Action</Text>
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
              <Stat>
                <StatLabel>Current Price</StatLabel>
                <StatNumber>${formatValue(technicalData.current_price)}</StatNumber>
                <StatHelpText>
                  <StatArrow type={technicalData.price_change >= 0 ? 'increase' : 'decrease'} />
                  {formatValue(Math.abs(technicalData.price_change))}%
                </StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Volume</StatLabel>
                <StatNumber>{formatValue(technicalData.volume, 0)}</StatNumber>
                <StatHelpText>24h Volume</StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>High</StatLabel>
                <StatNumber>${formatValue(technicalData.high)}</StatNumber>
                <StatHelpText>24h High</StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Low</StatLabel>
                <StatNumber>${formatValue(technicalData.low)}</StatNumber>
                <StatHelpText>24h Low</StatHelpText>
              </Stat>
            </SimpleGrid>
          </Box>

          {/* Technical Indicators */}
          <Box>
            <Text fontWeight="semibold" mb={3}>Technical Indicators</Text>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
              {/* RSI */}
              {technicalData.rsi && (
                <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                  <HStack justify="space-between">
                    <VStack align="start" spacing={1}>
                      <Text fontSize="sm" color="gray.500">RSI (14)</Text>
                      <Text fontSize="xl" fontWeight="bold">
                        {formatValue(technicalData.rsi)}
                      </Text>
                    </VStack>
                    <Badge colorScheme={getIndicatorColor(technicalData.rsi, 'rsi')}>
                      {technicalData.rsi > 70 ? 'Overbought' : 
                       technicalData.rsi < 30 ? 'Oversold' : 'Neutral'}
                    </Badge>
                  </HStack>
                </Box>
              )}

              {/* MACD */}
              {technicalData.macd && (
                <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                  <HStack justify="space-between">
                    <VStack align="start" spacing={1}>
                      <Text fontSize="sm" color="gray.500">MACD</Text>
                      <Text fontSize="xl" fontWeight="bold">
                        {formatValue(technicalData.macd.macd)}
                      </Text>
                    </VStack>
                    <Badge colorScheme={getIndicatorColor(technicalData.macd.macd, 'macd')}>
                      {technicalData.macd.macd > 0 ? 'Bullish' : 'Bearish'}
                    </Badge>
                  </HStack>
                </Box>
              )}

              {/* Moving Averages */}
              {technicalData.moving_averages && (
                <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                  <VStack align="start" spacing={2}>
                    <Text fontSize="sm" color="gray.500">Moving Averages</Text>
                    {Object.entries(technicalData.moving_averages).map(([period, value]) => (
                      <HStack key={period} justify="space-between" w="full">
                        <Text fontSize="sm">MA{period}</Text>
                        <Text fontSize="sm" fontWeight="semibold">
                          ${formatValue(value)}
                        </Text>
                      </HStack>
                    ))}
                  </VStack>
                </Box>
              )}

              {/* Bollinger Bands */}
              {technicalData.bollinger_bands && (
                <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                  <VStack align="start" spacing={2}>
                    <Text fontSize="sm" color="gray.500">Bollinger Bands</Text>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">Upper</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        ${formatValue(technicalData.bollinger_bands.upper)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">Middle</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        ${formatValue(technicalData.bollinger_bands.middle)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">Lower</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        ${formatValue(technicalData.bollinger_bands.lower)}
                      </Text>
                    </HStack>
                  </VStack>
                </Box>
              )}

              {/* Stochastic */}
              {technicalData.stochastic && (
                <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                  <VStack align="start" spacing={2}>
                    <Text fontSize="sm" color="gray.500">Stochastic</Text>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">%K</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        {formatValue(technicalData.stochastic.k)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">%D</Text>
                      <Text fontSize="sm" fontWeight="semibold">
                        {formatValue(technicalData.stochastic.d)}
                      </Text>
                    </HStack>
                  </VStack>
                </Box>
              )}

              {/* Support/Resistance */}
              {technicalData.support_resistance && (
                <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                  <VStack align="start" spacing={2}>
                    <Text fontSize="sm" color="gray.500">Support & Resistance</Text>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">Resistance</Text>
                      <Text fontSize="sm" fontWeight="semibold" color="red.500">
                        ${formatValue(technicalData.support_resistance.resistance)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between" w="full">
                      <Text fontSize="sm">Support</Text>
                      <Text fontSize="sm" fontWeight="semibold" color="green.500">
                        ${formatValue(technicalData.support_resistance.support)}
                      </Text>
                    </HStack>
                  </VStack>
                </Box>
              )}
            </SimpleGrid>
          </Box>

          {/* Overall Signal */}
          {technicalData.signal && (
            <Box>
              <Text fontWeight="semibold" mb={3}>Technical Signal</Text>
              <HStack>
                <Badge 
                  size="lg" 
                  colorScheme={
                    technicalData.signal === 'BUY' ? 'green' :
                    technicalData.signal === 'SELL' ? 'red' : 'yellow'
                  }
                  p={2}
                >
                  {technicalData.signal}
                </Badge>
                {technicalData.confidence && (
                  <Text fontSize="sm" color="gray.500">
                    Confidence: {formatValue(technicalData.confidence * 100)}%
                  </Text>
                )}
              </HStack>
            </Box>
          )}
        </VStack>
      </CardBody>
    </MotionCard>
  );
};

export default TechnicalChart;
