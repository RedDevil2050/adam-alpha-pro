import React from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  HStack,
  VStack,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  useColorModeValue,
} from '@chakra-ui/react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

const MarketOverviewCard = ({ data, isLoading, error }) => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  if (isLoading) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardBody>
          <VStack spacing={4}>
            <Spinner size="lg" color="brand.500" />
            <Text>Loading market data...</Text>
          </VStack>
        </CardBody>
      </Card>
    );
  }

  if (error) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardBody>
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            Failed to load market data
          </Alert>
        </CardBody>
      </Card>
    );
  }

  const mockMarketData = {
    indices: [
      { name: 'S&P 500', value: '4,127.83', change: '+0.85%', trend: 'up' },
      { name: 'NASDAQ', value: '12,431.21', change: '+1.24%', trend: 'up' },
      { name: 'DOW', value: '33,945.58', change: '+0.43%', trend: 'up' },
      { name: 'NIFTY 50', value: '19,674.25', change: '-0.32%', trend: 'down' },
    ],
    marketStatus: 'OPEN',
    lastUpdate: new Date().toLocaleTimeString(),
  };

  const marketData = data?.data || mockMarketData;

  return (
    <MotionBox
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardHeader>
          <HStack justify="space-between">
            <Heading size="md">Market Overview</Heading>
            <HStack>
              <Badge
                colorScheme={marketData.marketStatus === 'OPEN' ? 'green' : 'red'}
                variant="solid"
              >
                <HStack spacing={1}>
                  <Activity size={12} />
                  <Text>{marketData.marketStatus}</Text>
                </HStack>
              </Badge>
              <Text fontSize="sm" color="gray.500">
                Updated: {marketData.lastUpdate}
              </Text>
            </HStack>
          </HStack>
        </CardHeader>
        <CardBody pt={0}>
          <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={4}>
            {marketData.indices.map((index, i) => (
              <MotionBox
                key={index.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.1 }}
              >
                <Box
                  p={4}
                  borderRadius="lg"
                  bg={useColorModeValue('gray.50', 'gray.700')}
                  border="1px"
                  borderColor={useColorModeValue('gray.200', 'gray.600')}
                  _hover={{ borderColor: 'brand.300' }}
                  transition="all 0.2s"
                >
                  <Stat size="sm">
                    <StatLabel fontSize="xs" color="gray.500">
                      {index.name}
                    </StatLabel>
                    <StatNumber fontSize="lg" fontWeight="bold">
                      {index.value}
                    </StatNumber>
                    <StatHelpText mb={0}>
                      <HStack spacing={1}>
                        {index.trend === 'up' ? (
                          <TrendingUp size={14} color="green" />
                        ) : (
                          <TrendingDown size={14} color="red" />
                        )}
                        <Text
                          color={index.trend === 'up' ? 'green.500' : 'red.500'}
                          fontWeight="medium"
                        >
                          {index.change}
                        </Text>
                      </HStack>
                    </StatHelpText>
                  </Stat>
                </Box>
              </MotionBox>
            ))}
          </Grid>
        </CardBody>
      </Card>
    </MotionBox>
  );
};

export default MarketOverviewCard;
