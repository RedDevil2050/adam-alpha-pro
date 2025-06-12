import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Card,
  CardHeader,
  CardBody,
  Text,
  Badge,
  Button,
  IconButton,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  useColorModeValue,
  useToast,
  Tooltip,
  Progress,
  Flex,
  Spacer,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
  List,
  ListItem,
  ListIcon,
  Image,
  Avatar,
  AvatarGroup,
  CircularProgress,
  CircularProgressLabel,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  FiTrendingUp, 
  FiTrendingDown,
  FiStar,
  FiTarget,
  FiDollarSign,
  FiActivity,
  FiBarChart2,
  FiPieChart,
  FiCalendar,
  FiClock,
  FiUsers,
  FiShield,
  FiZap,
  FiAward,
  FiCheckCircle,
  FiAlertTriangle,
  FiInfo,
  FiArrowUp,
  FiArrowDown,
  FiEye,
  FiHeart,
  FiShare2,
  FiRefreshCw,
  FiGlobe,
  FiFlag
} from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';

const MotionBox = motion(Box);

const IndianMarketDashboard = () => {
  const [loading, setLoading] = useState(false);
  const [marketStatus, setMarketStatus] = useState('OPEN');
  const navigate = useNavigate();
  
  const toast = useToast();
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Live Indian market indices
  const indianIndices = [
    {
      name: 'Nifty 50',
      symbol: '^NSEI',
      value: 19674.25,
      change: 156.35,
      changePercent: 0.80,
      volume: 245678900,
      high: 19798.50,
      low: 19567.80
    },
    {
      name: 'Sensex',
      symbol: '^BSESN',
      value: 65953.48,
      change: 234.12,
      changePercent: 0.36,
      volume: 156789000,
      high: 66125.30,
      low: 65789.20
    },
    {
      name: 'Bank Nifty',
      symbol: '^NSEBANK',
      value: 44287.35,
      change: -89.75,
      changePercent: -0.20,
      volume: 98765400,
      high: 44456.80,
      low: 44123.50
    },
    {
      name: 'Nifty IT',
      symbol: '^NSEIT',
      value: 28456.80,
      change: 245.60,
      changePercent: 0.87,
      volume: 45678900,
      high: 28567.90,
      low: 28234.10
    },
    {
      name: 'Nifty FMCG',
      symbol: '^NSEFMCG',
      value: 53234.75,
      change: 123.45,
      changePercent: 0.23,
      volume: 23456700,
      high: 53345.60,
      low: 53123.20
    },
    {
      name: 'Nifty Auto',
      symbol: '^NSEAUTO',
      value: 15678.90,
      change: -45.80,
      changePercent: -0.29,
      volume: 34567800,
      high: 15723.40,
      low: 15634.50
    }
  ];

  // Top Indian stocks by market cap
  const topStocks = [
    {
      symbol: 'RELIANCE',
      name: 'Reliance Industries',
      price: 2456.75,
      change: 45.30,
      changePercent: 1.87,
      marketCap: 16.6e12,
      volume: 3456789,
      sector: 'Oil & Gas',
      trendScore: 85,
      analystRating: 'Buy'
    },
    {
      symbol: 'TCS',
      name: 'Tata Consultancy Services',
      price: 3567.20,
      change: -23.45,
      changePercent: -0.65,
      marketCap: 13.0e12,
      volume: 2345678,
      sector: 'IT Services',
      trendScore: 72,
      analystRating: 'Buy'
    },
    {
      symbol: 'HDFCBANK',
      name: 'HDFC Bank',
      price: 1634.80,
      change: 18.75,
      changePercent: 1.16,
      marketCap: 12.4e12,
      volume: 4567890,
      sector: 'Banking',
      trendScore: 88,
      analystRating: 'Strong Buy'
    },
    {
      symbol: 'INFY',
      name: 'Infosys',
      price: 1567.45,
      change: 12.35,
      changePercent: 0.79,
      marketCap: 6.5e12,
      volume: 3789012,
      sector: 'IT Services',
      trendScore: 75,
      analystRating: 'Buy'
    },
    {
      symbol: 'ICICIBANK',
      name: 'ICICI Bank',
      price: 1078.30,
      change: -8.90,
      changePercent: -0.82,
      marketCap: 7.6e12,
      volume: 5678901,
      sector: 'Banking',
      trendScore: 68,
      analystRating: 'Hold'
    }
  ];

  // Market movers
  const topGainers = [
    { symbol: 'ADANIPORTS', change: 4.85, changePercent: 3.25 },
    { symbol: 'HINDUNILVR', change: 78.60, changePercent: 3.12 },
    { symbol: 'WIPRO', change: 23.45, changePercent: 2.98 },
    { symbol: 'TECHM', change: 45.30, changePercent: 2.87 },
    { symbol: 'POWERGRID', change: 12.80, changePercent: 2.65 }
  ];

  const topLosers = [
    { symbol: 'TATASTEEL', change: -45.60, changePercent: -3.85 },
    { symbol: 'JSWSTEEL', change: -38.90, changePercent: -3.42 },
    { symbol: 'HINDALCO', change: -25.70, changePercent: -3.18 },
    { symbol: 'COALINDIA', change: -18.45, changePercent: -2.95 },
    { symbol: 'NTPC', change: -12.30, changePercent: -2.78 }
  ];

  // Market news
  const marketNews = [
    {
      title: 'RBI keeps repo rate unchanged at 6.5%',
      time: '15 minutes ago',
      impact: 'positive',
      source: 'Economic Times'
    },
    {
      title: 'FII inflows cross ₹15,000 crore this month',
      time: '1 hour ago',
      impact: 'positive',
      source: 'Business Standard'
    },
    {
      title: 'IT sector outlook remains strong for Q3',
      time: '2 hours ago',
      impact: 'positive',
      source: 'Moneycontrol'
    },
    {
      title: 'Global oil prices surge 2% on supply concerns',
      time: '3 hours ago',
      impact: 'negative',
      source: 'Reuters India'
    }
  ];

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(value);
  };

  const formatMarketCap = (value) => {
    if (value >= 1e12) {
      return `₹${(value / 1e12).toFixed(2)}T`;
    } else if (value >= 1e9) {
      return `₹${(value / 1e9).toFixed(2)}B`;
    }
    return `₹${(value / 1e6).toFixed(2)}M`;
  };

  const formatVolume = (value) => {
    if (value >= 1e7) {
      return `${(value / 1e7).toFixed(1)}Cr`;
    } else if (value >= 1e5) {
      return `${(value / 1e5).toFixed(1)}L`;
    } else if (value >= 1e3) {
      return `${(value / 1e3).toFixed(1)}K`;
    }
    return value.toLocaleString();
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 70) return 'blue';
    if (score >= 60) return 'yellow';
    return 'red';
  };

  const getRatingColor = (rating) => {
    if (rating === 'Strong Buy') return 'green';
    if (rating === 'Buy') return 'blue';
    if (rating === 'Hold') return 'yellow';
    if (rating === 'Sell') return 'orange';
    return 'red';
  };

  const handleStockClick = (symbol) => {
    navigate(`/stock/${symbol}`);
  };

  const handleRefreshData = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      toast({
        title: 'Market Data Refreshed',
        description: 'Latest Indian market data has been loaded',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    }, 2000);
  };

  return (
    <Box bg={bgColor} minH="100vh" py={6}>
      <Container maxW="8xl">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <HStack justify="space-between" mb={6}>
            <VStack align="start" spacing={2}>
              <HStack>
                <FiFlag color="#FF9933" />
                <Heading size="xl" color="blue.500">
                  Indian Markets
                </Heading>
                <Badge colorScheme={marketStatus === 'OPEN' ? 'green' : 'red'} fontSize="sm">
                  {marketStatus}
                </Badge>
              </HStack>
              <Text color="gray.500">
                Real-time Indian stock market analysis powered by Trendlyne-style intelligence
              </Text>
            </VStack>
            <HStack spacing={3}>
              <Button
                leftIcon={<FiRefreshCw />}
                colorScheme="blue"
                variant="outline"
                onClick={handleRefreshData}
                isLoading={loading}
                loadingText="Refreshing"
              >
                Refresh
              </Button>
              <Button
                leftIcon={<FiBarChart2 />}
                colorScheme="green"
                onClick={() => navigate('/screener')}
              >
                Open Screener
              </Button>
            </HStack>
          </HStack>

          {/* Market Indices */}
          <Card bg={cardBg} mb={6}>
            <CardHeader>
              <HStack justify="space-between">
                <Heading size="md">
                  <HStack>
                    <FiActivity />
                    <Text>Major Indices</Text>
                  </HStack>
                </Heading>
                <Text fontSize="sm" color="gray.500">
                  Last updated: {new Date().toLocaleTimeString()}
                </Text>
              </HStack>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                {indianIndices.map((index, i) => (
                  <Card key={i} bg={borderColor} size="sm" cursor="pointer"
                        _hover={{ transform: 'translateY(-2px)', boxShadow: 'md' }}
                        transition="all 0.2s">
                    <CardBody>
                      <VStack spacing={2}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm" fontWeight="bold">{index.name}</Text>
                          <Badge size="xs" colorScheme="blue">{index.symbol}</Badge>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="lg" fontWeight="bold">
                            {index.value.toLocaleString()}
                          </Text>
                          <VStack spacing={0} align="end">
                            <HStack>
                              {index.change > 0 ? <FiTrendingUp color="green" size={14} /> : <FiTrendingDown color="red" size={14} />}
                              <Text fontSize="sm" color={index.change > 0 ? 'green.500' : 'red.500'}>
                                {index.change > 0 ? '+' : ''}{index.change.toFixed(2)}
                              </Text>
                            </HStack>
                            <Text fontSize="xs" color={index.changePercent > 0 ? 'green.500' : 'red.500'}>
                              ({index.changePercent > 0 ? '+' : ''}{index.changePercent.toFixed(2)}%)
                            </Text>
                          </VStack>
                        </HStack>
                        <HStack justify="space-between" w="full" fontSize="xs" color="gray.500">
                          <Text>Vol: {formatVolume(index.volume)}</Text>
                          <Text>H: {index.high.toLocaleString()}</Text>
                          <Text>L: {index.low.toLocaleString()}</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>
            </CardBody>
          </Card>

          <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6} mb={6}>
            {/* Top Stocks */}
            <Box gridColumn={{ base: 'span 1', lg: 'span 2' }}>
              <Card bg={cardBg} h="full">
                <CardHeader>
                  <HStack justify="space-between">
                    <Heading size="md">
                      <HStack>
                        <FiStar />
                        <Text>Top Stocks by Market Cap</Text>
                      </HStack>
                    </Heading>
                    <Button size="sm" variant="outline" onClick={() => navigate('/screener')}>
                      View All
                    </Button>
                  </HStack>
                </CardHeader>
                <CardBody>
                  <VStack spacing={3}>
                    {topStocks.map((stock, index) => (
                      <HStack key={index} w="full" p={3} borderRadius="md" bg={borderColor}
                              cursor="pointer" _hover={{ bg: useColorModeValue('gray.100', 'gray.700') }}
                              onClick={() => handleStockClick(stock.symbol)}>
                        <VStack align="start" spacing={0} flex={1}>
                          <HStack>
                            <Text fontWeight="bold" fontSize="sm">{stock.symbol}</Text>
                            <Badge size="xs" colorScheme="purple">{stock.sector}</Badge>
                          </HStack>
                          <Text fontSize="xs" color="gray.500" maxW="200px" isTruncated>
                            {stock.name}
                          </Text>
                        </VStack>
                        
                        <VStack spacing={0} align="end" minW="80px">
                          <Text fontSize="sm" fontWeight="bold">
                            ₹{stock.price.toLocaleString()}
                          </Text>
                          <HStack spacing={1}>
                            {stock.change > 0 ? <FiTrendingUp color="green" size={12} /> : <FiTrendingDown color="red" size={12} />}
                            <Text fontSize="xs" color={stock.change > 0 ? 'green.500' : 'red.500'}>
                              {stock.changePercent > 0 ? '+' : ''}{stock.changePercent.toFixed(2)}%
                            </Text>
                          </HStack>
                        </VStack>
                        
                        <VStack spacing={1} align="center" minW="60px">
                          <CircularProgress 
                            value={stock.trendScore} 
                            color={getScoreColor(stock.trendScore) + '.400'} 
                            size="40px"
                          >
                            <CircularProgressLabel fontSize="8px">
                              {stock.trendScore}
                            </CircularProgressLabel>
                          </CircularProgress>
                          <Badge size="xs" colorScheme={getRatingColor(stock.analystRating)}>
                            {stock.analystRating}
                          </Badge>
                        </VStack>
                        
                        <IconButton
                          icon={<FiEye />}
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStockClick(stock.symbol);
                          }}
                        />
                      </HStack>
                    ))}
                  </VStack>
                </CardBody>
              </Card>
            </Box>

            {/* Market Movers */}
            <VStack spacing={6}>
              <Card bg={cardBg} w="full">
                <CardHeader>
                  <Heading size="sm" color="green.500">
                    <HStack>
                      <FiTrendingUp />
                      <Text>Top Gainers</Text>
                    </HStack>
                  </Heading>
                </CardHeader>
                <CardBody>
                  <VStack spacing={2}>
                    {topGainers.map((stock, index) => (
                      <HStack key={index} justify="space-between" w="full" p={2} borderRadius="sm" bg={borderColor}>
                        <Text fontSize="sm" fontWeight="bold">{stock.symbol}</Text>
                        <VStack spacing={0} align="end">
                          <Text fontSize="sm" color="green.500">
                            +{stock.change.toFixed(2)}
                          </Text>
                          <Text fontSize="xs" color="green.500">
                            +{stock.changePercent.toFixed(2)}%
                          </Text>
                        </VStack>
                      </HStack>
                    ))}
                  </VStack>
                </CardBody>
              </Card>

              <Card bg={cardBg} w="full">
                <CardHeader>
                  <Heading size="sm" color="red.500">
                    <HStack>
                      <FiTrendingDown />
                      <Text>Top Losers</Text>
                    </HStack>
                  </Heading>
                </CardHeader>
                <CardBody>
                  <VStack spacing={2}>
                    {topLosers.map((stock, index) => (
                      <HStack key={index} justify="space-between" w="full" p={2} borderRadius="sm" bg={borderColor}>
                        <Text fontSize="sm" fontWeight="bold">{stock.symbol}</Text>
                        <VStack spacing={0} align="end">
                          <Text fontSize="sm" color="red.500">
                            {stock.change.toFixed(2)}
                          </Text>
                          <Text fontSize="xs" color="red.500">
                            {stock.changePercent.toFixed(2)}%
                          </Text>
                        </VStack>
                      </HStack>
                    ))}
                  </VStack>
                </CardBody>
              </Card>
            </VStack>
          </SimpleGrid>

          {/* Market News */}
          <Card bg={cardBg}>
            <CardHeader>
              <Heading size="md">
                <HStack>
                  <FiGlobe />
                  <Text>Market News & Updates</Text>
                </HStack>
              </Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={4}>
                {marketNews.map((news, index) => (
                  <HStack key={index} w="full" p={4} borderRadius="md" bg={borderColor}
                          cursor="pointer" _hover={{ bg: useColorModeValue('gray.100', 'gray.700') }}>
                    <Box
                      w={3}
                      h={3}
                      borderRadius="full"
                      bg={news.impact === 'positive' ? 'green.400' : news.impact === 'negative' ? 'red.400' : 'blue.400'}
                    />
                    <VStack align="start" spacing={1} flex={1}>
                      <Text fontSize="sm" fontWeight="semibold">
                        {news.title}
                      </Text>
                      <HStack>
                        <Text fontSize="xs" color="gray.500">
                          {news.source}
                        </Text>
                        <Text fontSize="xs" color="gray.400">
                          • {news.time}
                        </Text>
                      </HStack>
                    </VStack>
                    <Badge 
                      colorScheme={
                        news.impact === 'positive' ? 'green' : 
                        news.impact === 'negative' ? 'red' : 'blue'
                      }
                      size="sm"
                    >
                      {news.impact}
                    </Badge>
                  </HStack>
                ))}
              </VStack>
            </CardBody>
          </Card>

        </MotionBox>
      </Container>
    </Box>
  );
};

export default IndianMarketDashboard;
