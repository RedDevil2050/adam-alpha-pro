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
  Progress,
  useColorModeValue,
  useToast,
  Tooltip,
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
  CircularProgress,
  CircularProgressLabel,
  Image,
  Tab,
  Tabs,
  TabList,
  TabPanel,
  TabPanels,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  FiTrendingUp, 
  FiTrendingDown,
  FiStar,
  FiHeart,
  FiShare2,
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
  FiBookmark
} from 'react-icons/fi';

const MotionBox = motion(Box);

const StockDetailPage = ({ symbol = 'RELIANCE' }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [isWatchlisted, setIsWatchlisted] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const toast = useToast();
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Comprehensive stock data (similar to Trendlyne detail page)
  const stockData = {
    symbol: 'RELIANCE',
    name: 'Reliance Industries Limited',
    sector: 'Oil & Gas',
    industry: 'Integrated Oil & Gas',
    exchange: 'NSE',
    isin: 'INE002A01018',
    price: 2456.75,
    change: 45.30,
    changePercent: 1.87,
    volume: 3456789,
    avgVolume: 2890000,
    marketCap: 16.6e12,
    enterpriseValue: 17.2e12,
    sharesOutstanding: 6758000000,
    freeFloat: 49.7,
    
    // Valuation Metrics
    peRatio: 25.4,
    pegRatio: 1.8,
    pbRatio: 1.8,
    psRatio: 2.1,
    evEbitda: 12.5,
    priceToSales: 2.1,
    
    // Financial Metrics
    roe: 14.2,
    roa: 8.5,
    roic: 11.8,
    grossMargin: 38.5,
    operatingMargin: 18.2,
    netMargin: 12.1,
    debtEquity: 0.42,
    currentRatio: 1.25,
    quickRatio: 0.95,
    
    // Growth Metrics
    revenueGrowth1Y: 12.5,
    revenueGrowth3Y: 8.2,
    epsGrowth1Y: 15.8,
    epsGrowth3Y: 11.4,
    
    // Per Share Data
    eps: 96.8,
    bvps: 1367.5,
    salesPerShare: 1164.2,
    cashPerShare: 285.4,
    
    // Dividend Data
    divYield: 0.35,
    divPayoutRatio: 8.5,
    exDivDate: '2024-09-15',
    divGrowth5Y: 12.3,
    
    // Technical Indicators
    sma20: 2420.35,
    sma50: 2398.80,
    sma200: 2365.90,
    rsi: 68.5,
    macd: 15.2,
    bollingerUpper: 2580.25,
    bollingerLower: 2320.15,
    
    // Support & Resistance
    support1: 2400,
    support2: 2350,
    resistance1: 2550,
    resistance2: 2650,
    weekHigh52: 2968,
    weekLow52: 2173,
    
    // Analyst Data
    analystRating: 'Buy',
    priceTarget: 2750,
    priceTargetHigh: 3200,
    priceTargetLow: 2400,
    analystCount: 35,
    strongBuy: 15,
    buy: 12,
    hold: 6,
    sell: 2,
    strongSell: 0,
    
    // Quality Scores (Trendlyne style)
    trendScore: 85,
    qualityScore: 92,
    momentumScore: 78,
    valueScore: 82,
    technicalRating: 'Strong Buy',
    fundamentalRating: 'Buy',
    
    // Ownership Structure
    promoterHolding: 50.3,
    fiiHolding: 24.8,
    diiHolding: 14.2,
    retailHolding: 10.7,
    
    // Recent Results
    lastQuarter: {
      revenue: 2.3e11,
      revenueGrowth: 15.2,
      netProfit: 1.8e10,
      profitGrowth: 18.5,
      eps: 12.5,
      epsGrowth: 18.5
    },
    
    // Business Segments
    segments: [
      { name: 'Petroleum Refining', revenue: 45.2, margin: 8.5 },
      { name: 'Petrochemicals', revenue: 32.1, margin: 15.2 },
      { name: 'Oil & Gas Exploration', revenue: 12.3, margin: 22.8 },
      { name: 'Retail', revenue: 8.9, margin: 5.2 },
      { name: 'Digital Services', revenue: 1.5, margin: 45.2 }
    ],
    
    // Key Events
    events: [
      { date: '2024-07-15', event: 'Q1 Results', impact: 'positive' },
      { date: '2024-08-20', event: 'Dividend Declaration', impact: 'positive' },
      { date: '2024-09-10', event: 'AGM', impact: 'neutral' },
      { date: '2024-10-15', event: 'Q2 Results Expected', impact: 'neutral' }
    ]
  };

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

  const handleWatchlist = () => {
    setIsWatchlisted(!isWatchlisted);
    toast({
      title: isWatchlisted ? 'Removed from Watchlist' : 'Added to Watchlist',
      description: `${stockData.symbol} has been ${isWatchlisted ? 'removed from' : 'added to'} your watchlist`,
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
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
          <Card bg={cardBg} mb={6}>
            <CardBody>
              <Flex align="center" justify="space-between">
                <HStack spacing={4}>
                  <VStack align="start" spacing={0}>
                    <HStack>
                      <Heading size="lg" color="blue.500">{stockData.symbol}</Heading>
                      <Badge colorScheme="blue" fontSize="xs">{stockData.exchange}</Badge>
                    </HStack>
                    <Text fontSize="md" color="gray.600" maxW="400px">
                      {stockData.name}
                    </Text>
                    <HStack spacing={4} mt={2}>
                      <Badge colorScheme="purple">{stockData.sector}</Badge>
                      <Text fontSize="sm" color="gray.500">{stockData.industry}</Text>
                    </HStack>
                  </VStack>
                  
                  <VStack align="end" spacing={0}>
                    <Heading size="xl" color={stockData.change > 0 ? 'green.500' : 'red.500'}>
                      {formatCurrency(stockData.price)}
                    </Heading>
                    <HStack>
                      {stockData.change > 0 ? <FiTrendingUp color="green" /> : <FiTrendingDown color="red" />}
                      <Text color={stockData.change > 0 ? 'green.500' : 'red.500'} fontWeight="semibold">
                        {stockData.change > 0 ? '+' : ''}{stockData.change.toFixed(2)} ({stockData.changePercent > 0 ? '+' : ''}{stockData.changePercent.toFixed(2)}%)
                      </Text>
                    </HStack>
                    <Text fontSize="sm" color="gray.500">
                      Volume: {(stockData.volume / 1e6).toFixed(1)}M
                    </Text>
                  </VStack>
                </HStack>
                
                <VStack spacing={2}>
                  <HStack spacing={2}>
                    <Tooltip label={isWatchlisted ? "Remove from Watchlist" : "Add to Watchlist"}>
                      <IconButton
                        icon={<FiHeart />}
                        colorScheme={isWatchlisted ? "red" : "gray"}
                        variant={isWatchlisted ? "solid" : "outline"}
                        onClick={handleWatchlist}
                      />
                    </Tooltip>
                    <Tooltip label="Share">
                      <IconButton icon={<FiShare2 />} variant="outline" />
                    </Tooltip>
                    <Tooltip label="View Chart">
                      <IconButton icon={<FiBarChart2 />} variant="outline" />
                    </Tooltip>
                  </HStack>
                  <Text fontSize="xs" color="gray.500">
                    Last updated: {new Date().toLocaleTimeString()}
                  </Text>
                </VStack>
              </Flex>
            </CardBody>
          </Card>

          {/* Key Metrics */}
          <SimpleGrid columns={{ base: 2, md: 4, lg: 6 }} spacing={4} mb={6}>
            <Card bg={cardBg} size="sm">
              <CardBody>
                <Stat size="sm">
                  <StatLabel>Market Cap</StatLabel>
                  <StatNumber fontSize="lg">{formatMarketCap(stockData.marketCap)}</StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card bg={cardBg} size="sm">
              <CardBody>
                <Stat size="sm">
                  <StatLabel>P/E Ratio</StatLabel>
                  <StatNumber fontSize="lg">{stockData.peRatio}</StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card bg={cardBg} size="sm">
              <CardBody>
                <Stat size="sm">
                  <StatLabel>ROE</StatLabel>
                  <StatNumber fontSize="lg">{stockData.roe}%</StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card bg={cardBg} size="sm">
              <CardBody>
                <Stat size="sm">
                  <StatLabel>Debt/Equity</StatLabel>
                  <StatNumber fontSize="lg">{stockData.debtEquity}</StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card bg={cardBg} size="sm">
              <CardBody>
                <Stat size="sm">
                  <StatLabel>Div Yield</StatLabel>
                  <StatNumber fontSize="lg">{stockData.divYield}%</StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card bg={cardBg} size="sm">
              <CardBody>
                <Stat size="sm">
                  <StatLabel>52W High</StatLabel>
                  <StatNumber fontSize="lg">₹{stockData.weekHigh52}</StatNumber>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Quality Scores */}
          <Card bg={cardBg} mb={6}>
            <CardHeader>
              <Heading size="md">
                <HStack>
                  <FiAward />
                  <Text>Trendlyne Quality Scores</Text>
                </HStack>
              </Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
                <VStack>
                  <CircularProgress value={stockData.trendScore} color={getScoreColor(stockData.trendScore) + '.400'} size="80px">
                    <CircularProgressLabel fontSize="sm" fontWeight="bold">
                      {stockData.trendScore}
                    </CircularProgressLabel>
                  </CircularProgress>
                  <Text fontSize="sm" fontWeight="semibold">Trend Score</Text>
                  <Badge colorScheme={getScoreColor(stockData.trendScore)} size="sm">
                    {stockData.trendScore >= 80 ? 'Excellent' : stockData.trendScore >= 70 ? 'Good' : stockData.trendScore >= 60 ? 'Average' : 'Poor'}
                  </Badge>
                </VStack>
                
                <VStack>
                  <CircularProgress value={stockData.qualityScore} color={getScoreColor(stockData.qualityScore) + '.400'} size="80px">
                    <CircularProgressLabel fontSize="sm" fontWeight="bold">
                      {stockData.qualityScore}
                    </CircularProgressLabel>
                  </CircularProgress>
                  <Text fontSize="sm" fontWeight="semibold">Quality Score</Text>
                  <Badge colorScheme={getScoreColor(stockData.qualityScore)} size="sm">
                    {stockData.qualityScore >= 80 ? 'Excellent' : stockData.qualityScore >= 70 ? 'Good' : stockData.qualityScore >= 60 ? 'Average' : 'Poor'}
                  </Badge>
                </VStack>
                
                <VStack>
                  <CircularProgress value={stockData.momentumScore} color={getScoreColor(stockData.momentumScore) + '.400'} size="80px">
                    <CircularProgressLabel fontSize="sm" fontWeight="bold">
                      {stockData.momentumScore}
                    </CircularProgressLabel>
                  </CircularProgress>
                  <Text fontSize="sm" fontWeight="semibold">Momentum Score</Text>
                  <Badge colorScheme={getScoreColor(stockData.momentumScore)} size="sm">
                    {stockData.momentumScore >= 80 ? 'Excellent' : stockData.momentumScore >= 70 ? 'Good' : stockData.momentumScore >= 60 ? 'Average' : 'Poor'}
                  </Badge>
                </VStack>
                
                <VStack>
                  <CircularProgress value={stockData.valueScore} color={getScoreColor(stockData.valueScore) + '.400'} size="80px">
                    <CircularProgressLabel fontSize="sm" fontWeight="bold">
                      {stockData.valueScore}
                    </CircularProgressLabel>
                  </CircularProgress>
                  <Text fontSize="sm" fontWeight="semibold">Value Score</Text>
                  <Badge colorScheme={getScoreColor(stockData.valueScore)} size="sm">
                    {stockData.valueScore >= 80 ? 'Excellent' : stockData.valueScore >= 70 ? 'Good' : stockData.valueScore >= 60 ? 'Average' : 'Poor'}
                  </Badge>
                </VStack>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Detailed Analysis Tabs */}
          <Tabs index={activeTab} onChange={setActiveTab} variant="enclosed" bg={cardBg} borderRadius="lg">
            <TabList>
              <Tab>
                <HStack>
                  <FiBarChart2 />
                  <Text>Technical</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiDollarSign />
                  <Text>Fundamentals</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiTarget />
                  <Text>Analyst Views</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiPieChart />
                  <Text>Ownership</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiActivity />
                  <Text>Results</Text>
                </HStack>
              </Tab>
              <Tab>
                <HStack>
                  <FiCalendar />
                  <Text>Events</Text>
                </HStack>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Technical Analysis */}
              <TabPanel>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Technical Indicators</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">RSI (14)</Text>
                          <Badge colorScheme={stockData.rsi > 70 ? 'red' : stockData.rsi < 30 ? 'green' : 'blue'}>
                            {stockData.rsi}
                          </Badge>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">SMA 20</Text>
                          <Text fontSize="sm">₹{stockData.sma20}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">SMA 50</Text>
                          <Text fontSize="sm">₹{stockData.sma50}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">SMA 200</Text>
                          <Text fontSize="sm">₹{stockData.sma200}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">MACD</Text>
                          <Text fontSize="sm" color={stockData.macd > 0 ? 'green.500' : 'red.500'}>
                            {stockData.macd}
                          </Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Support & Resistance</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Resistance 2</Text>
                          <Text fontSize="sm" color="red.500">₹{stockData.resistance2}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Resistance 1</Text>
                          <Text fontSize="sm" color="red.400">₹{stockData.resistance1}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm" fontWeight="bold">Current Price</Text>
                          <Text fontSize="sm" fontWeight="bold">₹{stockData.price}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Support 1</Text>
                          <Text fontSize="sm" color="green.400">₹{stockData.support1}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Support 2</Text>
                          <Text fontSize="sm" color="green.500">₹{stockData.support2}</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>

                <Card bg={cardBg} mt={6}>
                  <CardHeader>
                    <Heading size="sm">Technical Rating</Heading>
                  </CardHeader>
                  <CardBody>
                    <HStack justify="space-between">
                      <Text>Overall Technical Rating</Text>
                      <Badge colorScheme={getRatingColor(stockData.technicalRating)} size="lg">
                        {stockData.technicalRating}
                      </Badge>
                    </HStack>
                  </CardBody>
                </Card>
              </TabPanel>

              {/* Fundamentals */}
              <TabPanel>
                <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Valuation Ratios</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">P/E Ratio</Text>
                          <Text fontSize="sm">{stockData.peRatio}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">P/B Ratio</Text>
                          <Text fontSize="sm">{stockData.pbRatio}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">P/S Ratio</Text>
                          <Text fontSize="sm">{stockData.psRatio}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">EV/EBITDA</Text>
                          <Text fontSize="sm">{stockData.evEbitda}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">PEG Ratio</Text>
                          <Text fontSize="sm">{stockData.pegRatio}</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Profitability</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">ROE</Text>
                          <Text fontSize="sm">{stockData.roe}%</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">ROA</Text>
                          <Text fontSize="sm">{stockData.roa}%</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">ROIC</Text>
                          <Text fontSize="sm">{stockData.roic}%</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Gross Margin</Text>
                          <Text fontSize="sm">{stockData.grossMargin}%</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Net Margin</Text>
                          <Text fontSize="sm">{stockData.netMargin}%</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Financial Health</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Debt/Equity</Text>
                          <Text fontSize="sm">{stockData.debtEquity}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Current Ratio</Text>
                          <Text fontSize="sm">{stockData.currentRatio}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Quick Ratio</Text>
                          <Text fontSize="sm">{stockData.quickRatio}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Revenue Growth (1Y)</Text>
                          <Text fontSize="sm" color="green.500">{stockData.revenueGrowth1Y}%</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">EPS Growth (1Y)</Text>
                          <Text fontSize="sm" color="green.500">{stockData.epsGrowth1Y}%</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>

                <Card bg={cardBg} mt={6}>
                  <CardHeader>
                    <Heading size="sm">Business Segments</Heading>
                  </CardHeader>
                  <CardBody>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Segment</Th>
                          <Th isNumeric>Revenue %</Th>
                          <Th isNumeric>Margin %</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {stockData.segments.map((segment, index) => (
                          <Tr key={index}>
                            <Td>{segment.name}</Td>
                            <Td isNumeric>{segment.revenue}%</Td>
                            <Td isNumeric color={segment.margin > 15 ? 'green.500' : 'orange.500'}>
                              {segment.margin}%
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </CardBody>
                </Card>
              </TabPanel>

              {/* Analyst Views */}
              <TabPanel>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Analyst Recommendations</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Strong Buy</Text>
                          <Badge colorScheme="green">{stockData.strongBuy}</Badge>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Buy</Text>
                          <Badge colorScheme="blue">{stockData.buy}</Badge>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Hold</Text>
                          <Badge colorScheme="yellow">{stockData.hold}</Badge>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Sell</Text>
                          <Badge colorScheme="orange">{stockData.sell}</Badge>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Strong Sell</Text>
                          <Badge colorScheme="red">{stockData.strongSell}</Badge>
                        </HStack>
                        <Divider />
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm" fontWeight="bold">Total Analysts</Text>
                          <Text fontSize="sm" fontWeight="bold">{stockData.analystCount}</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Price Targets</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Average Target</Text>
                          <Text fontSize="sm" fontWeight="bold">₹{stockData.priceTarget}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">High Target</Text>
                          <Text fontSize="sm" color="green.500">₹{stockData.priceTargetHigh}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Low Target</Text>
                          <Text fontSize="sm" color="red.500">₹{stockData.priceTargetLow}</Text>
                        </HStack>
                        <Divider />
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Current Price</Text>
                          <Text fontSize="sm">₹{stockData.price}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm" fontWeight="bold">Upside Potential</Text>
                          <Text fontSize="sm" fontWeight="bold" color="green.500">
                            {((stockData.priceTarget - stockData.price) / stockData.price * 100).toFixed(1)}%
                          </Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>

                <Card bg={cardBg} mt={6}>
                  <CardHeader>
                    <Heading size="sm">Overall Analyst Rating</Heading>
                  </CardHeader>
                  <CardBody>
                    <HStack justify="space-between">
                      <Text>Consensus Rating</Text>
                      <Badge colorScheme={getRatingColor(stockData.analystRating)} size="lg">
                        {stockData.analystRating}
                      </Badge>
                    </HStack>
                  </CardBody>
                </Card>
              </TabPanel>

              {/* Ownership */}
              <TabPanel>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Shareholding Pattern</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Promoter Holdings</Text>
                          <Text fontSize="sm" fontWeight="bold">{stockData.promoterHolding}%</Text>
                        </HStack>
                        <Progress value={stockData.promoterHolding} colorScheme="blue" size="sm" w="full" />
                        
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">FII Holdings</Text>
                          <Text fontSize="sm" fontWeight="bold">{stockData.fiiHolding}%</Text>
                        </HStack>
                        <Progress value={stockData.fiiHolding} colorScheme="green" size="sm" w="full" />
                        
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">DII Holdings</Text>
                          <Text fontSize="sm" fontWeight="bold">{stockData.diiHolding}%</Text>
                        </HStack>
                        <Progress value={stockData.diiHolding} colorScheme="purple" size="sm" w="full" />
                        
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Retail Holdings</Text>
                          <Text fontSize="sm" fontWeight="bold">{stockData.retailHolding}%</Text>
                        </HStack>
                        <Progress value={stockData.retailHolding} colorScheme="orange" size="sm" w="full" />
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="sm">Share Details</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Outstanding Shares</Text>
                          <Text fontSize="sm">{(stockData.sharesOutstanding / 1e9).toFixed(2)}B</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Free Float</Text>
                          <Text fontSize="sm">{stockData.freeFloat}%</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Market Cap</Text>
                          <Text fontSize="sm">{formatMarketCap(stockData.marketCap)}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Enterprise Value</Text>
                          <Text fontSize="sm">{formatMarketCap(stockData.enterpriseValue)}</Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Avg Daily Volume</Text>
                          <Text fontSize="sm">{(stockData.avgVolume / 1e6).toFixed(1)}M</Text>
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </TabPanel>

              {/* Results */}
              <TabPanel>
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="sm">Latest Quarter Results</Heading>
                  </CardHeader>
                  <CardBody>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                      <VStack spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Revenue</Text>
                          <VStack align="end" spacing={0}>
                            <Text fontSize="sm" fontWeight="bold">{formatMarketCap(stockData.lastQuarter.revenue)}</Text>
                            <Text fontSize="xs" color="green.500">+{stockData.lastQuarter.revenueGrowth}% YoY</Text>
                          </VStack>
                        </HStack>
                        
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Net Profit</Text>
                          <VStack align="end" spacing={0}>
                            <Text fontSize="sm" fontWeight="bold">{formatMarketCap(stockData.lastQuarter.netProfit)}</Text>
                            <Text fontSize="xs" color="green.500">+{stockData.lastQuarter.profitGrowth}% YoY</Text>
                          </VStack>
                        </HStack>
                        
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">EPS</Text>
                          <VStack align="end" spacing={0}>
                            <Text fontSize="sm" fontWeight="bold">₹{stockData.lastQuarter.eps}</Text>
                            <Text fontSize="xs" color="green.500">+{stockData.lastQuarter.epsGrowth}% YoY</Text>
                          </VStack>
                        </HStack>
                      </VStack>
                      
                      <Alert status="success" borderRadius="md">
                        <AlertIcon />
                        <VStack align="start" spacing={1}>
                          <AlertTitle fontSize="sm">Strong Performance</AlertTitle>
                          <AlertDescription fontSize="xs">
                            Company delivered robust growth across all key metrics in the latest quarter.
                          </AlertDescription>
                        </VStack>
                      </Alert>
                    </SimpleGrid>
                  </CardBody>
                </Card>
              </TabPanel>

              {/* Events */}
              <TabPanel>
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="sm">Corporate Events & Calendar</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4}>
                      {stockData.events.map((event, index) => (
                        <HStack key={index} justify="space-between" w="full" p={3} borderRadius="md" bg={borderColor}>
                          <HStack>
                            <FiCalendar />
                            <VStack align="start" spacing={0}>
                              <Text fontSize="sm" fontWeight="bold">{event.event}</Text>
                              <Text fontSize="xs" color="gray.500">{event.date}</Text>
                            </VStack>
                          </HStack>
                          <Badge 
                            colorScheme={
                              event.impact === 'positive' ? 'green' : 
                              event.impact === 'negative' ? 'red' : 'gray'
                            }
                          >
                            {event.impact}
                          </Badge>
                        </HStack>
                      ))}
                    </VStack>
                  </CardBody>
                </Card>
              </TabPanel>
            </TabPanels>
          </Tabs>

        </MotionBox>
      </Container>
    </Box>
  );
};

export default StockDetailPage;
