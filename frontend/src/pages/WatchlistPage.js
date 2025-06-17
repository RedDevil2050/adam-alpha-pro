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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Alert,
  AlertIcon,
  AlertDescription,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import LiveDataTicker from '../components/common/LiveDataTicker';
import LiveDataCard from '../components/common/LiveDataCard';
import { 
  FiSearch, 
  FiPlus, 
  FiTrash2, 
  FiTrendingUp, 
  FiTrendingDown,
  FiStar,
  FiEye,
  FiBarChart2
} from 'react-icons/fi';

const MotionBox = motion(Box);

const WatchlistPage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedList, setSelectedList] = useState('default');
  const [newSymbol, setNewSymbol] = useState('');
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  // Mock watchlist data
  const watchlists = {
    default: {
      name: 'My Watchlist',
      symbols: [
        {
          symbol: 'AAPL',
          name: 'Apple Inc.',
          price: 175.50,
          change: 2.30,
          changePercent: 1.33,
          volume: 45678900,
          marketCap: 2.85e12,
          peRatio: 29.5,
          alerts: 2
        },
        {
          symbol: 'MSFT',
          name: 'Microsoft Corporation',
          price: 338.25,
          change: -1.85,
          changePercent: -0.54,
          volume: 23456700,
          marketCap: 2.51e12,
          peRatio: 32.1,
          alerts: 0
        },
        {
          symbol: 'GOOGL',
          name: 'Alphabet Inc.',
          price: 128.75,
          change: 0.95,
          changePercent: 0.74,
          volume: 18765400,
          marketCap: 1.62e12,
          peRatio: 24.8,
          alerts: 1
        },
        {
          symbol: 'TSLA',
          name: 'Tesla Inc.',
          price: 205.30,
          change: -8.45,
          changePercent: -3.95,
          volume: 98765400,
          marketCap: 652e9,
          peRatio: 45.2,
          alerts: 3
        },
        {
          symbol: 'NVDA',
          name: 'NVIDIA Corporation',
          price: 478.90,
          change: 12.75,
          changePercent: 2.74,
          volume: 34567800,
          marketCap: 1.18e12,
          peRatio: 67.3,
          alerts: 1
        }
      ]
    },
    tech: {
      name: 'Technology',
      symbols: [
        {
          symbol: 'META',
          name: 'Meta Platforms Inc.',
          price: 325.40,
          change: 5.60,
          changePercent: 1.75,
          volume: 15678900,
          marketCap: 825e9,
          peRatio: 23.4,
          alerts: 0
        }
      ]
    }
  };

  const currentWatchlist = watchlists[selectedList] || watchlists.default;

  const filteredSymbols = currentWatchlist.symbols.filter(stock =>
    stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    stock.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddSymbol = () => {
    if (newSymbol.trim()) {
      toast({
        title: 'Symbol added',
        description: `${newSymbol.toUpperCase()} has been added to your watchlist.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      setNewSymbol('');
      onClose();
    }
  };

  const handleRemoveSymbol = (symbol) => {
    toast({
      title: 'Symbol removed',
      description: `${symbol} has been removed from your watchlist.`,
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatMarketCap = (value) => {
    if (value >= 1e12) {
      return `$${(value / 1e12).toFixed(2)}T`;
    } else if (value >= 1e9) {
      return `$${(value / 1e9).toFixed(2)}B`;
    } else if (value >= 1e6) {
      return `$${(value / 1e6).toFixed(2)}M`;
    }
    return formatCurrency(value);
  };

  const formatVolume = (value) => {
    if (value >= 1e6) {
      return `${(value / 1e6).toFixed(1)}M`;
    } else if (value >= 1e3) {
      return `${(value / 1e3).toFixed(1)}K`;
    }
    return value.toLocaleString();
  };

  const formatPercent = (value) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Calculate summary stats
  const totalValue = filteredSymbols.reduce((sum, stock) => sum + stock.price, 0);
  const gainers = filteredSymbols.filter(stock => stock.change > 0).length;
  const losers = filteredSymbols.filter(stock => stock.change < 0).length;
  const totalAlerts = filteredSymbols.reduce((sum, stock) => sum + stock.alerts, 0);
  return (
    <Box bg={bgColor} minH="100vh" py={8}>
      <Container maxW="7xl">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Live Data Ticker - Synchronized across all pages */}
          <Box mb={6}>
            <LiveDataTicker 
              symbols={['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR']}
              maxItems={5}
            />
          </Box>

          {/* Header */}
          <HStack justify="space-between" mb={8}>
            <VStack align="start" spacing={2}>
              <Heading size="xl">Watchlist</Heading>
              <Text color="gray.500">Monitor your favorite stocks and track alerts</Text>
            </VStack>
            <Button
              leftIcon={<FiPlus />}
              colorScheme="blue"
              onClick={onOpen}
            >
              Add Symbol
            </Button>
          </HStack>

          {/* Summary Stats */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6} mb={8}>
            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Total Symbols</StatLabel>
                  <StatNumber>{filteredSymbols.length}</StatNumber>
                  <StatHelpText>In current list</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Gainers</StatLabel>
                  <StatNumber color="green.500">{gainers}</StatNumber>
                  <StatHelpText>{((gainers / filteredSymbols.length) * 100).toFixed(0)}% of total</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Losers</StatLabel>
                  <StatNumber color="red.500">{losers}</StatNumber>
                  <StatHelpText>{((losers / filteredSymbols.length) * 100).toFixed(0)}% of total</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg}>
              <CardBody>
                <Stat>
                  <StatLabel>Active Alerts</StatLabel>
                  <StatNumber color="orange.500">{totalAlerts}</StatNumber>
                  <StatHelpText>Across all symbols</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Controls */}
          <HStack spacing={4} mb={6}>
            <InputGroup maxW="300px">
              <InputLeftElement pointerEvents="none">
                <FiSearch color="gray.300" />
              </InputLeftElement>
              <Input
                placeholder="Search symbols..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </InputGroup>
            <Select
              maxW="200px"
              value={selectedList}
              onChange={(e) => setSelectedList(e.target.value)}
            >
              <option value="default">My Watchlist</option>
              <option value="tech">Technology</option>
            </Select>
          </HStack>

          {/* Alerts */}
          {totalAlerts > 0 && (
            <Alert status="warning" borderRadius="md" mb={6}>
              <AlertIcon />
              <AlertDescription>
                You have {totalAlerts} active alert{totalAlerts > 1 ? 's' : ''} across your watchlist symbols.
              </AlertDescription>
            </Alert>
          )}

          {/* Watchlist Table */}
          <Card bg={cardBg}>
            <CardHeader>
              <HStack justify="space-between">
                <Heading size="md">{currentWatchlist.name}</Heading>
                <Text color="gray.500">{filteredSymbols.length} symbols</Text>
              </HStack>
            </CardHeader>
            <CardBody>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Symbol</Th>
                    <Th>Name</Th>
                    <Th isNumeric>Price</Th>
                    <Th isNumeric>Change</Th>
                    <Th isNumeric>%</Th>
                    <Th isNumeric>Volume</Th>
                    <Th isNumeric>Market Cap</Th>
                    <Th isNumeric>P/E</Th>
                    <Th>Alerts</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {filteredSymbols.map((stock) => (
                    <Tr key={stock.symbol}>
                      <Td>
                        <HStack>
                          <Text fontWeight="bold">{stock.symbol}</Text>
                          <IconButton
                            icon={<FiStar />}
                            size="xs"
                            variant="ghost"
                            color="yellow.500"
                            aria-label="Favorite"
                          />
                        </HStack>
                      </Td>
                      <Td>
                        <Text fontSize="sm" maxW="200px" isTruncated>
                          {stock.name}
                        </Text>
                      </Td>
                      <Td isNumeric fontWeight="semibold">
                        {formatCurrency(stock.price)}
                      </Td>
                      <Td isNumeric color={stock.change > 0 ? 'green.500' : 'red.500'}>
                        {stock.change > 0 ? '+' : ''}{stock.change.toFixed(2)}
                      </Td>
                      <Td isNumeric>
                        <HStack justify="flex-end">
                          {stock.changePercent > 0 ? 
                            <FiTrendingUp color="green" /> : 
                            <FiTrendingDown color="red" />
                          }
                          <Text color={stock.changePercent > 0 ? 'green.500' : 'red.500'}>
                            {formatPercent(stock.changePercent)}
                          </Text>
                        </HStack>
                      </Td>
                      <Td isNumeric fontSize="sm">
                        {formatVolume(stock.volume)}
                      </Td>
                      <Td isNumeric fontSize="sm">
                        {formatMarketCap(stock.marketCap)}
                      </Td>
                      <Td isNumeric fontSize="sm">
                        {stock.peRatio.toFixed(1)}
                      </Td>
                      <Td>
                        {stock.alerts > 0 && (
                          <Badge colorScheme="orange">
                            {stock.alerts}
                          </Badge>
                        )}
                      </Td>
                      <Td>
                        <HStack spacing={1}>
                          <IconButton
                            icon={<FiEye />}
                            size="sm"
                            variant="ghost"
                            aria-label="View details"
                          />                          <IconButton
                            icon={<FiBarChart2 />}
                            size="sm"
                            variant="ghost"
                            aria-label="Analyze"
                          />
                          <IconButton
                            icon={<FiTrash2 />}
                            size="sm"
                            variant="ghost"
                            colorScheme="red"
                            aria-label="Remove"
                            onClick={() => handleRemoveSymbol(stock.symbol)}
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </CardBody>
          </Card>

          {/* Add Symbol Modal */}
          <Modal isOpen={isOpen} onClose={onClose}>
            <ModalOverlay />
            <ModalContent>
              <ModalHeader>Add Symbol to Watchlist</ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                <VStack spacing={4}>
                  <FormControl>
                    <FormLabel>Symbol</FormLabel>
                    <Input
                      placeholder="Enter stock symbol (e.g., AAPL)"
                      value={newSymbol}
                      onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                    />
                  </FormControl>
                  <FormControl>
                    <FormLabel>Watchlist</FormLabel>
                    <Select value={selectedList} onChange={(e) => setSelectedList(e.target.value)}>
                      <option value="default">My Watchlist</option>
                      <option value="tech">Technology</option>
                    </Select>
                  </FormControl>
                </VStack>
              </ModalBody>
              <ModalFooter>
                <Button variant="ghost" mr={3} onClick={onClose}>
                  Cancel
                </Button>
                <Button colorScheme="blue" onClick={handleAddSymbol}>
                  Add Symbol
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
        </MotionBox>
      </Container>
    </Box>
  );
};

export default WatchlistPage;
