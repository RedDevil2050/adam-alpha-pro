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
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  useToast,
  Tooltip,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tab,
  Tabs,
  TabList,
  TabPanel,
  TabPanels,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  FiSearch, 
  FiFilter, 
  FiTrendingUp, 
  FiTrendingDown,
  FiStar,
  FiEye,
  FiBarChart2,
  FiTarget,
  FiActivity,
  FiRefreshCw,
  FiDownload,
  FiShare2,
  FiHeart,
  FiZap,
  FiPieChart,
  FiGlobe
} from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import ApiService from '../../services/api';

const MotionBox = motion(Box);

const IndianStockScreener = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [sector, setSector] = useState('all');
  const [priceRange, setPriceRange] = useState('all');
  const [marketCap, setMarketCap] = useState('all');
  const [peRange, setPeRange] = useState('all');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [indianStocks, setIndianStocks] = useState([]);
  const [marketIndices, setMarketIndices] = useState([]);
  
  const navigate = useNavigate();
  const toast = useToast();
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Load Indian stocks and market data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      // Test backend connectivity first
      const backendTest = await ApiService.testBackendConnection();
      console.log('Backend connectivity:', backendTest);

      // Try to load real data from API
      const [stocksData, indicesData] = await Promise.all([
        ApiService.getIndianStockList(),
        ApiService.getIndianMarketIndices()
      ]);
      
      setIndianStocks(stocksData.stocks || []);
      setMarketIndices(indicesData.indices || []);
      
      toast({
        title: 'Data Loaded',
        description: `Latest Indian market data loaded. Backend: ${backendTest.success ? 'Connected' : 'Using fallback'}`,
        status: backendTest.success ? 'success' : 'warning',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error loading data:', error);
      toast({
        title: 'Using Demo Data',
        description: 'Backend unavailable. Showing sample Indian stock data.',
        status: 'info',
        duration: 3000,
        isClosable: true,
      });
      
      // Fallback to comprehensive demo data
      setIndianStocks([
        {
          symbol: 'RELIANCE',
          name: 'Reliance Industries Ltd',
          sector: 'Oil & Gas',
          price: 2456.75,
          change: 45.30,
          changePercent: 1.87,
          volume: 3456789,
          marketCap: 16.6e12,
          peRatio: 25.4,
          pbRatio: 1.8,
          divYield: 0.35,
          roe: 14.2,
          debt_equity: 0.42,
          eps: 96.8,
          trendScore: 85,
          qualityScore: 92,
          momentumScore: 78,
          valueScore: 82,
          technicalRating: 'Strong Buy',
          fundamentalRating: 'Buy',
          analystRating: 'Buy',
          priceTarget: 2750,
          support: 2400,
          resistance: 2550,
          weekHigh52: 2968,
          weekLow52: 2173,
          avgVolume: 2890000,
          fiiHolding: 24.8,
          diiHolding: 14.2,
          promoterHolding: 50.3,
          retailHolding: 10.7
        },
        {
          symbol: 'TCS',
          name: 'Tata Consultancy Services Ltd',
          sector: 'IT Services',
          price: 3567.20,
          change: -23.45,
          changePercent: -0.65,
          volume: 2345678,
          marketCap: 13.0e12,
          peRatio: 28.9,
          pbRatio: 12.5,
          divYield: 1.25,
          roe: 44.2,
          debt_equity: 0.05,
          eps: 123.5,
          trendScore: 72,
          qualityScore: 96,
          momentumScore: 65,
          valueScore: 75,
          technicalRating: 'Hold',
          fundamentalRating: 'Strong Buy',
          analystRating: 'Buy',
          priceTarget: 3850,
          support: 3450,
          resistance: 3650,
          weekHigh52: 4259,
          weekLow52: 3056,
          avgVolume: 1890000,
          fiiHolding: 45.2,
          diiHolding: 8.5,
          promoterHolding: 72.0,
          retailHolding: 14.3
        },
        {
          symbol: 'HDFCBANK',
          name: 'HDFC Bank Ltd',
          sector: 'Banking',
          price: 1634.80,
          change: 18.75,
          changePercent: 1.16,
          volume: 4567890,
          marketCap: 12.4e12,
          peRatio: 19.2,
          pbRatio: 2.8,
          divYield: 1.1,
          roe: 17.8,
          debt_equity: 0.0,
          eps: 85.2,
          trendScore: 88,
          qualityScore: 94,
          momentumScore: 82,
          valueScore: 78,
          technicalRating: 'Buy',
          fundamentalRating: 'Strong Buy',
          analystRating: 'Buy',
          priceTarget: 1800,
          support: 1580,
          resistance: 1680,
          weekHigh52: 1884,
          weekLow52: 1351,
          avgVolume: 2980000,
          fiiHolding: 35.2,
          diiHolding: 15.8,
          promoterHolding: 13.0,
          retailHolding: 36.0
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Filter stocks based on criteria
  const filteredStocks = indianStocks.filter(stock => {
    const matchesSearch = stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         stock.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSector = sector === 'all' || stock.sector === sector;
    const matchesPrice = priceRange === 'all' || 
                        (priceRange === 'under500' && stock.price < 500) ||
                        (priceRange === '500-1000' && stock.price >= 500 && stock.price < 1000) ||
                        (priceRange === '1000-2000' && stock.price >= 1000 && stock.price < 2000) ||
                        (priceRange === 'above2000' && stock.price >= 2000);
    const matchesMarketCap = marketCap === 'all' ||
                           (marketCap === 'large' && stock.marketCap >= 1e12) ||
                           (marketCap === 'mid' && stock.marketCap >= 50e9 && stock.marketCap < 1e12) ||
                           (marketCap === 'small' && stock.marketCap < 50e9);
    const matchesPE = peRange === 'all' ||
                     (peRange === 'under15' && stock.peRatio < 15) ||
                     (peRange === '15-25' && stock.peRatio >= 15 && stock.peRatio < 25) ||
                     (peRange === '25-35' && stock.peRatio >= 25 && stock.peRatio < 35) ||
                     (peRange === 'above35' && stock.peRatio >= 35);
    
    return matchesSearch && matchesSector && matchesPrice && matchesMarketCap && matchesPE;
  });

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
    if (value >= 1e6) {
      return `${(value / 1e6).toFixed(1)}M`;
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

  const sectors = ['all', 'Banking', 'IT Services', 'Oil & Gas', 'FMCG', 'Pharmaceuticals', 'Automobile', 'Metals'];

  const handleRefreshData = () => {
    loadInitialData();
  };

  const handleAddToWatchlist = (stock) => {
    toast({
      title: 'Added to Watchlist',
      description: `${stock.symbol} has been added to your watchlist`,
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
  };

  const handleStockClick = (symbol) => {
    navigate(`/stock/${symbol}`);
  };

  const marketStats = {
    nifty50: { value: 19674.25, change: 156.35, changePercent: 0.8 },
    sensex: { value: 65953.48, change: 234.12, changePercent: 0.36 },
    bankNifty: { value: 44287.35, change: -89.75, changePercent: -0.2 },
    niftyIT: { value: 28456.80, change: 245.60, changePercent: 0.87 }
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
              <Heading size="xl" color="blue.500">
                Indian Stock Screener
              </Heading>
              <Text color="gray.500">
                Discover, analyze and track Indian stocks like Trendlyne
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
                Refresh Data
              </Button>
              <Button
                leftIcon={<FiDownload />}
                colorScheme="green"
                variant="outline"
              >
                Export
              </Button>
            </HStack>
          </HStack>

          {/* Market Overview */}
          <Card bg={cardBg} mb={6}>
            <CardHeader>
              <Heading size="md">Market Overview</Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
                <Stat>
                  <StatLabel>Nifty 50</StatLabel>
                  <StatNumber color={marketStats.nifty50.change > 0 ? 'green.500' : 'red.500'}>
                    {marketStats.nifty50.value.toLocaleString()}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={marketStats.nifty50.change > 0 ? 'increase' : 'decrease'} />
                    {marketStats.nifty50.changePercent}%
                  </StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>Sensex</StatLabel>
                  <StatNumber color={marketStats.sensex.change > 0 ? 'green.500' : 'red.500'}>
                    {marketStats.sensex.value.toLocaleString()}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={marketStats.sensex.change > 0 ? 'increase' : 'decrease'} />
                    {marketStats.sensex.changePercent}%
                  </StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>Bank Nifty</StatLabel>
                  <StatNumber color={marketStats.bankNifty.change > 0 ? 'green.500' : 'red.500'}>
                    {marketStats.bankNifty.value.toLocaleString()}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={marketStats.bankNifty.change > 0 ? 'increase' : 'decrease'} />
                    {marketStats.bankNifty.changePercent}%
                  </StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>Nifty IT</StatLabel>
                  <StatNumber color={marketStats.niftyIT.change > 0 ? 'green.500' : 'red.500'}>
                    {marketStats.niftyIT.value.toLocaleString()}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={marketStats.niftyIT.change > 0 ? 'increase' : 'decrease'} />
                    {marketStats.niftyIT.changePercent}%
                  </StatHelpText>
                </Stat>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Filters */}
          <Card bg={cardBg} mb={6}>
            <CardHeader>
              <HStack justify="space-between">
                <Heading size="md">
                  <HStack>
                    <FiFilter />
                    <Text>Screen Stocks</Text>
                  </HStack>
                </Heading>
                <Text color="gray.500">{filteredStocks.length} stocks found</Text>
              </HStack>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 5 }} spacing={4}>
                <InputGroup>
                  <InputLeftElement pointerEvents="none">
                    <FiSearch color="gray.300" />
                  </InputLeftElement>
                  <Input
                    placeholder="Search stocks..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </InputGroup>
                
                <Select value={sector} onChange={(e) => setSector(e.target.value)}>
                  <option value="all">All Sectors</option>
                  {sectors.slice(1).map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </Select>

                <Select value={priceRange} onChange={(e) => setPriceRange(e.target.value)}>
                  <option value="all">All Prices</option>
                  <option value="under500">Under ₹500</option>
                  <option value="500-1000">₹500 - ₹1000</option>
                  <option value="1000-2000">₹1000 - ₹2000</option>
                  <option value="above2000">Above ₹2000</option>
                </Select>

                <Select value={marketCap} onChange={(e) => setMarketCap(e.target.value)}>
                  <option value="all">All Cap</option>
                  <option value="large">Large Cap</option>
                  <option value="mid">Mid Cap</option>
                  <option value="small">Small Cap</option>
                </Select>

                <Select value={peRange} onChange={(e) => setPeRange(e.target.value)}>
                  <option value="all">All P/E</option>
                  <option value="under15">P/E &lt; 15</option>
                  <option value="15-25">P/E 15-25</option>
                  <option value="25-35">P/E 25-35</option>
                  <option value="above35">P/E &gt; 35</option>
                </Select>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Stock Analysis Tabs */}
          <Tabs index={activeTab} onChange={setActiveTab} variant="enclosed" bg={cardBg} borderRadius="lg">
            <TabList>
              <Tab>
                <HStack>
                  <FiActivity />
                  <Text>Technical View</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiPieChart />
                  <Text>Fundamental View</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiZap />
                  <Text>Quality Scores</Text>
                </HStack>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Technical Analysis Tab */}
              <TabPanel p={0}>
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Stock</Th>
                        <Th isNumeric>Price</Th>
                        <Th isNumeric>Change</Th>
                        <Th isNumeric>Volume</Th>
                        <Th>Technical Rating</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {filteredStocks.map((stock) => (
                        <Tr key={stock.symbol} _hover={{ bg: borderColor }} cursor="pointer">
                          <Td onClick={() => handleStockClick(stock.symbol)}>
                            <VStack align="start" spacing={1}>
                              <Text fontWeight="bold" fontSize="sm">{stock.symbol}</Text>
                              <Text fontSize="xs" color="gray.500" maxW="120px" isTruncated>
                                {stock.name}
                              </Text>
                              <Badge size="sm" colorScheme="blue">{stock.sector}</Badge>
                            </VStack>
                          </Td>
                          <Td isNumeric fontWeight="semibold">
                            {formatCurrency(stock.price)}
                          </Td>
                          <Td isNumeric>
                            <VStack spacing={0}>
                              <Text color={stock.change > 0 ? 'green.500' : 'red.500'} fontSize="sm">
                                {stock.change > 0 ? '+' : ''}{stock.change?.toFixed(2) || 0}
                              </Text>
                              <Text color={stock.changePercent > 0 ? 'green.500' : 'red.500'} fontSize="xs">
                                ({stock.changePercent > 0 ? '+' : ''}{stock.changePercent?.toFixed(2) || 0}%)
                              </Text>
                            </VStack>
                          </Td>
                          <Td isNumeric fontSize="sm">
                            {formatVolume(stock.volume || 0)}
                          </Td>
                          <Td>
                            <Badge colorScheme={getRatingColor(stock.technicalRating)} size="sm">
                              {stock.technicalRating || 'N/A'}
                            </Badge>
                          </Td>
                          <Td>
                            <HStack spacing={1}>
                              <Tooltip label="Add to Watchlist">
                                <IconButton
                                  icon={<FiHeart />}
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleAddToWatchlist(stock)}
                                />
                              </Tooltip>
                              <Tooltip label="View Chart">
                                <IconButton
                                  icon={<FiBarChart2 />}
                                  size="sm"
                                  variant="ghost"
                                />
                              </Tooltip>
                            </HStack>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </TabPanel>

              {/* Fundamental Analysis Tab */}
              <TabPanel p={0}>
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Stock</Th>
                        <Th isNumeric>Market Cap</Th>
                        <Th isNumeric>P/E</Th>
                        <Th isNumeric>P/B</Th>
                        <Th isNumeric>ROE</Th>
                        <Th isNumeric>D/E</Th>
                        <Th>Fund Rating</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {filteredStocks.map((stock) => (
                        <Tr key={stock.symbol} _hover={{ bg: borderColor }} cursor="pointer">
                          <Td onClick={() => handleStockClick(stock.symbol)}>
                            <VStack align="start" spacing={1}>
                              <Text fontWeight="bold" fontSize="sm">{stock.symbol}</Text>
                              <Text fontSize="xs" color="gray.500" maxW="120px" isTruncated>
                                {stock.name}
                              </Text>
                              <Badge size="sm" colorScheme="blue">{stock.sector}</Badge>
                            </VStack>
                          </Td>
                          <Td isNumeric fontSize="sm">
                            {formatMarketCap(stock.marketCap || 0)}
                          </Td>
                          <Td isNumeric fontSize="sm">{stock.peRatio || 'N/A'}</Td>
                          <Td isNumeric fontSize="sm">{stock.pbRatio || 'N/A'}</Td>
                          <Td isNumeric fontSize="sm">{stock.roe || 'N/A'}%</Td>
                          <Td isNumeric fontSize="sm">{stock.debt_equity || 'N/A'}</Td>
                          <Td>
                            <Badge colorScheme={getRatingColor(stock.fundamentalRating)} size="sm">
                              {stock.fundamentalRating || 'N/A'}
                            </Badge>
                          </Td>
                          <Td>
                            <HStack spacing={1}>
                              <Tooltip label="Add to Watchlist">
                                <IconButton
                                  icon={<FiHeart />}
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleAddToWatchlist(stock)}
                                />
                              </Tooltip>
                              <Tooltip label="View Details">
                                <IconButton
                                  icon={<FiEye />}
                                  size="sm"
                                  variant="ghost"
                                />
                              </Tooltip>
                            </HStack>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </TabPanel>

              {/* Quality Scores Tab */}
              <TabPanel p={0}>
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Stock</Th>
                        <Th>Trend Score</Th>
                        <Th>Quality Score</Th>
                        <Th>Overall Rating</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {filteredStocks.map((stock) => (
                        <Tr key={stock.symbol} _hover={{ bg: borderColor }} cursor="pointer">
                          <Td onClick={() => handleStockClick(stock.symbol)}>
                            <VStack align="start" spacing={1}>
                              <Text fontWeight="bold" fontSize="sm">{stock.symbol}</Text>
                              <Text fontSize="xs" color="gray.500" maxW="120px" isTruncated>
                                {stock.name}
                              </Text>
                              <Badge size="sm" colorScheme="blue">{stock.sector}</Badge>
                            </VStack>
                          </Td>
                          <Td>
                            <VStack spacing={1}>
                              <Progress 
                                value={stock.trendScore || 0} 
                                colorScheme={getScoreColor(stock.trendScore || 0)}
                                size="sm"
                                w="60px"
                              />
                              <Text fontSize="xs">{stock.trendScore || 0}/100</Text>
                            </VStack>
                          </Td>
                          <Td>
                            <VStack spacing={1}>
                              <Progress 
                                value={stock.qualityScore || 0} 
                                colorScheme={getScoreColor(stock.qualityScore || 0)}
                                size="sm"
                                w="60px"
                              />
                              <Text fontSize="xs">{stock.qualityScore || 0}/100</Text>
                            </VStack>
                          </Td>
                          <Td>
                            <Badge colorScheme={getRatingColor(stock.analystRating)} size="sm">
                              {stock.analystRating || 'N/A'}
                            </Badge>
                          </Td>
                          <Td>
                            <HStack spacing={1}>
                              <Tooltip label="Add to Watchlist">
                                <IconButton
                                  icon={<FiHeart />}
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleAddToWatchlist(stock)}
                                />
                              </Tooltip>
                              <Tooltip label="Analyze">
                                <IconButton
                                  icon={<FiTarget />}
                                  size="sm"
                                  variant="ghost"
                                />
                              </Tooltip>
                            </HStack>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </TabPanel>
            </TabPanels>
          </Tabs>

          {/* Info Alert */}
          <Alert status="info" borderRadius="md" mt={6}>
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <AlertTitle fontSize="sm">Real-time Indian Stock Analysis</AlertTitle>
              <AlertDescription fontSize="xs">
                Data updated every 5 minutes during market hours. Technical and fundamental scores are calculated using proprietary algorithms.
              </AlertDescription>
            </VStack>
          </Alert>

        </MotionBox>
      </Container>
    </Box>
  );
};

export default IndianStockScreener;
