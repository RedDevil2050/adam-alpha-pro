import React, { useState } from 'react';
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
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  FiPieChart, 
  FiTrendingUp, 
  FiTrendingDown, 
  FiDollarSign,
  FiPercent,
  FiBarChart3,
  FiRefreshCw,
  FiSettings
} from 'react-icons/fi';

const MotionBox = motion(Box);

const PortfolioPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  // Mock portfolio data
  const portfolioData = {
    totalValue: 125750.30,
    totalGain: 12575.30,
    totalGainPercent: 11.12,
    dayChange: 2847.50,
    dayChangePercent: 2.31,
    holdings: [
      {
        symbol: 'AAPL',
        name: 'Apple Inc.',
        shares: 100,
        currentPrice: 175.50,
        totalValue: 17550,
        gain: 2550,
        gainPercent: 17.0,
        allocation: 13.95
      },
      {
        symbol: 'MSFT',
        name: 'Microsoft Corporation',
        shares: 75,
        currentPrice: 338.25,
        totalValue: 25369,
        gain: 4369,
        gainPercent: 20.8,
        allocation: 20.18
      },
      {
        symbol: 'GOOGL',
        name: 'Alphabet Inc.',
        shares: 50,
        currentPrice: 128.75,
        totalValue: 6438,
        gain: -562,
        gainPercent: -8.0,
        allocation: 5.12
      },
      {
        symbol: 'TSLA',
        name: 'Tesla Inc.',
        shares: 80,
        currentPrice: 205.30,
        totalValue: 16424,
        gain: 1424,
        gainPercent: 9.5,
        allocation: 13.05
      },
      {
        symbol: 'NVDA',
        name: 'NVIDIA Corporation',
        shares: 60,
        currentPrice: 478.90,
        totalValue: 28734,
        gain: 6734,
        gainPercent: 30.6,
        allocation: 22.85
      }
    ],
    sectors: [
      { name: 'Technology', value: 75231, percent: 59.8, color: 'blue' },
      { name: 'Consumer Discretionary', value: 16424, percent: 13.1, color: 'green' },
      { name: 'Communication Services', value: 6438, percent: 5.1, color: 'purple' },
      { name: 'Cash', value: 27657, percent: 22.0, color: 'gray' }
    ]
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => setIsLoading(false), 2000);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercent = (value) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <Box bg={bgColor} minH="100vh" py={8}>
      <Container maxW="7xl">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <HStack justify="space-between" mb={8}>
            <VStack align="start" spacing={2}>
              <Heading size="xl">Portfolio</Heading>
              <Text color="gray.500">Track your investments and performance</Text>
            </VStack>
            <HStack>
              <IconButton
                icon={<FiRefreshCw />}
                onClick={handleRefresh}
                isLoading={isLoading}
                variant="outline"
                aria-label="Refresh portfolio"
              />
              <IconButton
                icon={<FiSettings />}
                variant="outline"
                aria-label="Portfolio settings"
              />
            </HStack>
          </HStack>

          {/* Portfolio Summary */}
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Total Value</StatLabel>
                  <StatNumber>{formatCurrency(portfolioData.totalValue)}</StatNumber>
                  <StatHelpText>
                    <StatArrow type="increase" />
                    {formatPercent(portfolioData.totalGainPercent)}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Total Gain/Loss</StatLabel>
                  <StatNumber color={portfolioData.totalGain > 0 ? 'green.500' : 'red.500'}>
                    {formatCurrency(portfolioData.totalGain)}
                  </StatNumber>
                  <StatHelpText>All time</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Day Change</StatLabel>
                  <StatNumber color={portfolioData.dayChange > 0 ? 'green.500' : 'red.500'}>
                    {formatCurrency(portfolioData.dayChange)}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={portfolioData.dayChange > 0 ? "increase" : "decrease"} />
                    {formatPercent(portfolioData.dayChangePercent)}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Holdings</StatLabel>
                  <StatNumber>{portfolioData.holdings.length}</StatNumber>
                  <StatHelpText>Active positions</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Main Content */}
          <Tabs variant="enclosed" colorScheme="blue">
            <TabList>
              <Tab>Holdings</Tab>
              <Tab>Allocation</Tab>
              <Tab>Performance</Tab>
            </TabList>

            <TabPanels>
              {/* Holdings Tab */}
              <TabPanel p={0} pt={6}>
                <Card bg={cardBg}>
                  <CardHeader>
                    <Heading size="md">Current Holdings</Heading>
                  </CardHeader>
                  <CardBody>
                    <Table variant="simple">
                      <Thead>
                        <Tr>
                          <Th>Symbol</Th>
                          <Th>Name</Th>
                          <Th isNumeric>Shares</Th>
                          <Th isNumeric>Price</Th>
                          <Th isNumeric>Total Value</Th>
                          <Th isNumeric>Gain/Loss</Th>
                          <Th isNumeric>%</Th>
                          <Th isNumeric>Allocation</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {portfolioData.holdings.map((holding) => (
                          <Tr key={holding.symbol}>
                            <Td fontWeight="bold">{holding.symbol}</Td>
                            <Td>{holding.name}</Td>
                            <Td isNumeric>{holding.shares}</Td>
                            <Td isNumeric>{formatCurrency(holding.currentPrice)}</Td>
                            <Td isNumeric>{formatCurrency(holding.totalValue)}</Td>
                            <Td isNumeric color={holding.gain > 0 ? 'green.500' : 'red.500'}>
                              {formatCurrency(holding.gain)}
                            </Td>
                            <Td isNumeric color={holding.gainPercent > 0 ? 'green.500' : 'red.500'}>
                              {formatPercent(holding.gainPercent)}
                            </Td>
                            <Td isNumeric>{holding.allocation.toFixed(1)}%</Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </CardBody>
                </Card>
              </TabPanel>

              {/* Allocation Tab */}
              <TabPanel p={0} pt={6}>
                <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">Sector Allocation</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4} align="stretch">
                        {portfolioData.sectors.map((sector) => (
                          <Box key={sector.name}>
                            <HStack justify="space-between" mb={2}>
                              <Text fontWeight="semibold">{sector.name}</Text>
                              <HStack>
                                <Text fontSize="sm">{formatCurrency(sector.value)}</Text>
                                <Badge colorScheme={sector.color}>
                                  {sector.percent.toFixed(1)}%
                                </Badge>
                              </HStack>
                            </HStack>
                            <Progress
                              value={sector.percent}
                              colorScheme={sector.color}
                              size="sm"
                              borderRadius="md"
                            />
                          </Box>
                        ))}
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">Top Holdings</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4} align="stretch">
                        {portfolioData.holdings
                          .sort((a, b) => b.allocation - a.allocation)
                          .slice(0, 5)
                          .map((holding) => (
                            <Box key={holding.symbol}>
                              <HStack justify="space-between" mb={2}>
                                <VStack align="start" spacing={0}>
                                  <Text fontWeight="semibold">{holding.symbol}</Text>
                                  <Text fontSize="sm" color="gray.500">{holding.name}</Text>
                                </VStack>
                                <VStack align="end" spacing={0}>
                                  <Text fontWeight="semibold">{formatCurrency(holding.totalValue)}</Text>
                                  <Badge colorScheme={holding.gain > 0 ? 'green' : 'red'}>
                                    {holding.allocation.toFixed(1)}%
                                  </Badge>
                                </VStack>
                              </HStack>
                              <Progress
                                value={holding.allocation}
                                colorScheme={holding.gain > 0 ? 'green' : 'red'}
                                size="sm"
                                borderRadius="md"
                              />
                            </Box>
                          ))}
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </TabPanel>

              {/* Performance Tab */}
              <TabPanel p={0} pt={6}>
                <VStack spacing={6} align="stretch">
                  <Alert status="info" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>Portfolio Performance</AlertTitle>
                      <AlertDescription>
                        Your portfolio has outperformed the S&P 500 by 3.2% this year.
                        Consider rebalancing your technology allocation.
                      </AlertDescription>
                    </Box>
                  </Alert>

                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    <Card bg={cardBg}>
                      <CardHeader>
                        <Heading size="md">Performance Metrics</Heading>
                      </CardHeader>
                      <CardBody>
                        <SimpleGrid columns={2} spacing={4}>
                          <Stat>
                            <StatLabel>Sharpe Ratio</StatLabel>
                            <StatNumber>1.24</StatNumber>
                            <StatHelpText>Risk-adjusted return</StatHelpText>
                          </Stat>
                          <Stat>
                            <StatLabel>Beta</StatLabel>
                            <StatNumber>1.18</StatNumber>
                            <StatHelpText>Market correlation</StatHelpText>
                          </Stat>
                          <Stat>
                            <StatLabel>Max Drawdown</StatLabel>
                            <StatNumber color="red.500">-15.3%</StatNumber>
                            <StatHelpText>Worst decline</StatHelpText>
                          </Stat>
                          <Stat>
                            <StatLabel>Volatility</StatLabel>
                            <StatNumber>18.7%</StatNumber>
                            <StatHelpText>Annual volatility</StatHelpText>
                          </Stat>
                        </SimpleGrid>
                      </CardBody>
                    </Card>

                    <Card bg={cardBg}>
                      <CardHeader>
                        <Heading size="md">Benchmark Comparison</Heading>
                      </CardHeader>
                      <CardBody>
                        <VStack spacing={4} align="stretch">
                          <Box>
                            <HStack justify="space-between" mb={2}>
                              <Text>Your Portfolio</Text>
                              <Text color="green.500" fontWeight="bold">+11.12%</Text>
                            </HStack>
                            <Progress value={65} colorScheme="green" size="lg" borderRadius="md" />
                          </Box>
                          <Box>
                            <HStack justify="space-between" mb={2}>
                              <Text>S&P 500</Text>
                              <Text color="blue.500" fontWeight="bold">+7.92%</Text>
                            </HStack>
                            <Progress value={45} colorScheme="blue" size="lg" borderRadius="md" />
                          </Box>
                          <Box>
                            <HStack justify="space-between" mb={2}>
                              <Text>NASDAQ</Text>
                              <Text color="purple.500" fontWeight="bold">+9.45%</Text>
                            </HStack>
                            <Progress value={55} colorScheme="purple" size="lg" borderRadius="md" />
                          </Box>
                        </VStack>
                      </CardBody>
                    </Card>
                  </SimpleGrid>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </MotionBox>
      </Container>
    </Box>
  );
};

export default PortfolioPage;
