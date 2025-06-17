import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardHeader,
  CardBody,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
  Progress,
  Divider,
  SimpleGrid,
  Container,
  IconButton,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  BarChart3, 
  PieChart,
  RefreshCw,
  Wifi,
  Database,
  Globe,
  Target,
  Zap,
  Eye
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Cell,
  BarChart,
  Bar,
  AreaChart,
  Area,
  ComposedChart,
  Legend
} from 'recharts';
import { useQuery } from 'react-query';
import apiService from '../../services/api';

const MotionCard = motion(Card);
const MotionBox = motion(Box);

// Color schemes for charts
const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658'];
const TREND_COLORS = {
  up: '#48BB78',
  down: '#F56565',
  neutral: '#ED8936'
};

const LiveDataDashboard = () => {
  const [isLive, setIsLive] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const toast = useToast();
  
  const bg = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Fetch live market data
  const { data: liveData, isLoading: liveLoading, error: liveError, refetch: refetchLive } = useQuery(
    'live-market-data',
    () => apiService.getLiveIndianStocks(),
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      onSuccess: () => {
        setLastUpdate(new Date());
        if (!isLive) setIsLive(true);
      },
      onError: () => {
        setIsLive(false);
        toast({
          title: 'Live Data Connection Lost',
          description: 'Retrying connection...',
          status: 'warning',
          duration: 3000,
        });
      }
    }
  );

  // Fetch market state
  const { data: marketState, isLoading: marketLoading } = useQuery(
    'market-state',
    () => apiService.getLiveMarketStatus(),
    {
      refetchInterval: 60000, // Refetch every minute
    }
  );

  // Fetch stealth agent status
  const { data: agentStatus } = useQuery(
    'stealth-agents',
    () => apiService.getStealthAgentStatus(),
    {
      refetchInterval: 45000,
    }
  );

  if (liveLoading || marketLoading) {
    return (
      <Container maxW="full" py={8}>
        <VStack spacing={8}>
          <Spinner size="xl" color="blue.500" />
          <Text>Loading live market data...</Text>
        </VStack>
      </Container>
    );
  }

  if (liveError) {
    return (
      <Container maxW="full" py={8}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <VStack align="start" spacing={2}>
            <Text fontWeight="bold">Failed to load live data</Text>
            <Text fontSize="sm">Please check your backend connection</Text>
          </VStack>
        </Alert>
      </Container>
    );
  }

  const stocks = liveData?.data?.stocks || liveData?.stocks || [];
  const indices = marketState?.data?.indices || [];
  const marketStatus = marketState?.data?.market_status || 'unknown';

  // Prepare data for charts
  const stockPerformanceData = stocks.map(stock => ({
    symbol: stock.symbol,
    change: stock.change_percent,
    price: stock.price,
    volume: stock.volume,
    trend: stock.trend
  }));

  const sectorData = prepareSectorData(stocks);
  const trendData = prepareTrendData(stocks);
  const volumeData = stocks.slice(0, 5).map(stock => ({
    symbol: stock.symbol,
    volume: stock.volume,
    price: stock.price
  }));

  return (
    <Box bg={bg} minH="100vh" p={6}>
      <Container maxW="full">
        {/* Header Section */}
        <MotionBox
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          mb={8}
        >
          <VStack spacing={4} align="stretch">
            <HStack justify="space-between" align="center">
              <VStack align="start" spacing={1}>
                <Heading size="xl" color="blue.600">
                  🇮🇳 Zion Live Market Dashboard
                </Heading>
                <Text color="gray.600" fontSize="lg">
                  Real-time Indian equity market analysis powered by stealth agents
                </Text>
              </VStack>
              
              <HStack spacing={3}>
                <LiveStatusIndicator isLive={isLive} lastUpdate={lastUpdate} />
                <Tooltip label="Refresh Data">
                  <IconButton
                    icon={<RefreshCw />}
                    onClick={() => refetchLive()}
                    colorScheme="blue"
                    variant="outline"
                    isLoading={liveLoading}
                  />
                </Tooltip>
              </HStack>
            </HStack>

            {/* Market Status Bar */}
            <MarketStatusBar 
              marketStatus={marketStatus} 
              indices={indices}
              totalStocks={stocks.length}
            />
          </VStack>
        </MotionBox>

        {/* Main Dashboard Grid */}
        <Grid templateColumns="repeat(12, 1fr)" gap={6}>
          
          {/* Stock Performance Chart */}
          <MotionCard
            gridColumn="span 8"
            bg={cardBg}
            border="1px"
            borderColor={borderColor}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <CardHeader>
              <HStack>
                <BarChart3 size={20} color="#3182CE" />
                <Heading size="md">Live Stock Performance</Heading>
                <Badge colorScheme="green" variant="subtle">LIVE</Badge>
              </HStack>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={stockPerformanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <RechartsTooltip 
                    formatter={(value, name) => [
                      name === 'change' ? `${value}%` : `₹${value}`,
                      name === 'change' ? 'Change %' : name === 'price' ? 'Price' : 'Volume'
                    ]}
                  />
                  <Legend />
                  <Bar 
                    yAxisId="left" 
                    dataKey="change" 
                    fill="#8884d8" 
                    name="Change %"
                  />
                  <Line 
                    yAxisId="right" 
                    type="monotone" 
                    dataKey="price" 
                    stroke="#ff7300" 
                    name="Price ₹"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </CardBody>
          </MotionCard>

          {/* Market Sentiment Pie Chart */}
          <MotionCard
            gridColumn="span 4"
            bg={cardBg}
            border="1px"
            borderColor={borderColor}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <CardHeader>
              <HStack>
                <PieChart size={20} color="#38A169" />
                <Heading size="md">Market Sentiment</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={250}>
                <RechartsPieChart>
                  <pie
                    data={trendData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {trendData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </pie>
                  <RechartsTooltip />
                </RechartsPieChart>
              </ResponsiveContainer>
            </CardBody>
          </MotionCard>

          {/* Live Stock Cards */}
          <Box gridColumn="span 12">
            <Heading size="md" mb={4} display="flex" alignItems="center" gap={2}>
              <Activity size={20} color="#E53E3E" />
              Live Stock Data
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 5 }} spacing={4}>
              {stocks.slice(0, 10).map((stock, index) => (
                <LiveStockCard key={stock.symbol} stock={stock} index={index} />
              ))}
            </SimpleGrid>
          </Box>

          {/* Volume Analysis */}
          <MotionCard
            gridColumn="span 6"
            bg={cardBg}
            border="1px"
            borderColor={borderColor}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <CardHeader>
              <HStack>
                <Database size={20} color="#805AD5" />
                <Heading size="md">Volume Analysis</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={volumeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" />
                  <YAxis />
                  <RechartsTooltip 
                    formatter={(value) => [value.toLocaleString(), 'Volume']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="volume" 
                    stroke="#8884d8" 
                    fill="#8884d8" 
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardBody>
          </MotionCard>

          {/* Stealth Agents Status */}
          <MotionCard
            gridColumn="span 6"
            bg={cardBg}
            border="1px"
            borderColor={borderColor}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <CardHeader>
              <HStack>
                <Eye size={20} color="#D69E2E" />
                <Heading size="md">Stealth Agents Status</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <StealthAgentsDisplay agentStatus={agentStatus} />
            </CardBody>
          </MotionCard>

        </Grid>
      </Container>
    </Box>
  );
};

// Helper Components
const LiveStatusIndicator = ({ isLive, lastUpdate }) => (
  <HStack spacing={2}>
    <Box
      w={3}
      h={3}
      borderRadius="full"
      bg={isLive ? 'green.400' : 'red.400'}
      animation={isLive ? 'pulse 2s infinite' : 'none'}
    />
    <VStack spacing={0} align="start">
      <Text fontSize="xs" fontWeight="bold" color={isLive ? 'green.600' : 'red.600'}>
        {isLive ? 'LIVE' : 'OFFLINE'}
      </Text>
      <Text fontSize="xs" color="gray.500">
        {lastUpdate.toLocaleTimeString()}
      </Text>
    </VStack>
  </HStack>
);

const MarketStatusBar = ({ marketStatus, indices, totalStocks }) => {
  const statusColor = marketStatus === 'open' ? 'green' : 'red';
  
  return (
    <Card bg={useColorModeValue('blue.50', 'blue.900')} border="1px" borderColor="blue.200">
      <CardBody py={3}>
        <HStack justify="space-between" wrap="wrap" spacing={6}>
          <HStack>
            <Badge colorScheme={statusColor} variant="solid" fontSize="sm">
              MARKET {marketStatus.toUpperCase()}
            </Badge>
            <Text fontSize="sm" color="gray.600">
              {totalStocks} stocks tracked
            </Text>
          </HStack>
          
          <HStack spacing={8} wrap="wrap">
            {indices.slice(0, 4).map((index) => (
              <HStack key={index.symbol} spacing={2}>
                <Text fontWeight="bold" fontSize="sm">{index.name}:</Text>
                <Text fontSize="sm">{index.value}</Text>
                <Badge 
                  colorScheme={index.trend === 'up' ? 'green' : 'red'} 
                  variant="subtle"
                  fontSize="xs"
                >
                  {index.change}
                </Badge>
              </HStack>
            ))}
          </HStack>
        </HStack>
      </CardBody>
    </Card>
  );
};

const LiveStockCard = ({ stock, index }) => {
  const trendColor = TREND_COLORS[stock.trend] || TREND_COLORS.neutral;
  const TrendIcon = stock.trend === 'up' ? TrendingUp : TrendingDown;
  
  return (
    <MotionCard
      bg={useColorModeValue('white', 'gray.800')}
      border="1px"
      borderColor={useColorModeValue('gray.200', 'gray.700')}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      _hover={{ 
        transform: 'translateY(-2px)',
        shadow: 'lg',
        borderColor: trendColor
      }}
    >
      <CardBody p={4}>
        <VStack spacing={3} align="stretch">
          <HStack justify="space-between">
            <Text fontWeight="bold" fontSize="sm">{stock.symbol}</Text>
            <TrendIcon size={16} color={trendColor} />
          </HStack>
          
          <Stat size="sm">
            <StatNumber fontSize="lg">₹{stock.price?.toFixed(2) || 'N/A'}</StatNumber>
            <StatHelpText m={0}>
              <StatArrow type={stock.trend === 'up' ? 'increase' : 'decrease'} />
              {stock.change_percent?.toFixed(2) || '0.00'}%
            </StatHelpText>
          </Stat>
          
          <HStack justify="space-between" fontSize="xs" color="gray.500">
            <Text>Vol: {(stock.volume || 0).toLocaleString()}</Text>
            <Badge variant="outline" size="sm">
              {stock.trend?.toUpperCase() || 'NEUTRAL'}
            </Badge>
          </HStack>
        </VStack>
      </CardBody>
    </MotionCard>
  );
};

const StealthAgentsDisplay = ({ agentStatus }) => {
  const agents = [
    { name: 'MoneyControl', status: 'active', success: 98.5 },
    { name: 'TrendLyne', status: 'active', success: 96.2 },
    { name: 'StockEdge', status: 'active', success: 94.8 },
    { name: 'Screener', status: 'active', success: 99.1 },
    { name: 'TradingView', status: 'active', success: 97.3 }
  ];

  return (
    <VStack spacing={3} align="stretch">
      {agents.map((agent) => (
        <HStack key={agent.name} justify="space-between" p={2} bg="gray.50" borderRadius="md">
          <HStack>
            <Box w={2} h={2} borderRadius="full" bg="green.400" />
            <Text fontSize="sm" fontWeight="medium">{agent.name}</Text>
          </HStack>
          <HStack>
            <Progress 
              value={agent.success} 
              size="sm" 
              colorScheme="green" 
              w="60px"
              borderRadius="full"
            />
            <Text fontSize="xs" color="gray.600" minW="40px">
              {agent.success}%
            </Text>
          </HStack>
        </HStack>
      ))}
    </VStack>
  );
};

// Helper functions
const prepareSectorData = (stocks) => {
  const sectors = {};
  stocks.forEach(stock => {
    const sector = getSectorFromSymbol(stock.symbol);
    if (!sectors[sector]) sectors[sector] = { count: 0, totalChange: 0 };
    sectors[sector].count++;
    sectors[sector].totalChange += (stock.change_percent || 0);
  });
  
  return Object.entries(sectors).map(([sector, data]) => ({
    sector,
    count: data.count,
    avgChange: (data.totalChange / data.count).toFixed(2)
  }));
};

const prepareTrendData = (stocks) => {
  const trends = { up: 0, down: 0, neutral: 0 };
  stocks.forEach(stock => {
    trends[stock.trend || 'neutral']++;
  });
  
  return Object.entries(trends).map(([trend, count]) => ({
    name: trend.charAt(0).toUpperCase() + trend.slice(1),
    count,
    color: TREND_COLORS[trend]
  }));
};

const getSectorFromSymbol = (symbol) => {
  const sectorMap = {
    'RELIANCE': 'Oil & Gas',
    'TCS': 'IT Services',
    'INFY': 'IT Services', 
    'HDFCBANK': 'Banking',
    'ICICIBANK': 'Banking',
    'KOTAKBANK': 'Banking',
    'SBIN': 'Banking',
    'ITC': 'FMCG',
    'HINDUNILVR': 'FMCG',
    'BHARTIARTL': 'Telecom'
  };
  return sectorMap[symbol] || 'Others';
};

export default LiveDataDashboard;
