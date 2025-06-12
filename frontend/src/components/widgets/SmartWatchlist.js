import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  InputGroup,
  InputLeftElement,
  useColorModeValue,
  Card,
  CardBody,
  Badge,
  Flex,
  IconButton,
  useToast,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Search, Plus, Star, TrendingUp, Bell } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const MotionCard = motion(Card);

const SmartWatchlist = () => {
  const [newSymbol, setNewSymbol] = useState('');
  const [watchlist, setWatchlist] = useState([
    { symbol: 'RELIANCE', price: 2456.75, change: 23.45, changePercent: 0.96, alert: true },
    { symbol: 'TCS', price: 3567.80, change: -45.20, changePercent: -1.25, alert: false },
    { symbol: 'INFY', price: 1678.90, change: 34.56, changePercent: 2.10, alert: true },
    { symbol: 'HDFC', price: 2890.65, change: 12.30, changePercent: 0.43, alert: false },
  ]);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const navigate = useNavigate();
  const toast = useToast();

  const handleAddSymbol = () => {
    if (newSymbol.trim()) {
      const exists = watchlist.find(item => 
        item.symbol.toLowerCase() === newSymbol.toLowerCase()
      );
      
      if (!exists) {
        setWatchlist(prev => [...prev, {
          symbol: newSymbol.toUpperCase(),
          price: Math.random() * 3000 + 1000,
          change: (Math.random() - 0.5) * 100,
          changePercent: (Math.random() - 0.5) * 5,
          alert: false
        }]);
        setNewSymbol('');
        toast({
          title: 'Symbol Added',
          description: `${newSymbol.toUpperCase()} added to watchlist`,
          status: 'success',
          duration: 2000,
        });
      } else {
        toast({
          title: 'Symbol Exists',
          description: 'This symbol is already in your watchlist',
          status: 'warning',
          duration: 2000,
        });
      }
    }
  };

  const handleAnalyze = (symbol) => {
    navigate(`/analysis/${symbol}`);
  };

  const toggleAlert = (symbol) => {
    setWatchlist(prev => prev.map(item => 
      item.symbol === symbol 
        ? { ...item, alert: !item.alert }
        : item
    ));
  };

  return (
    <MotionCard
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      bg={cardBg}
      borderColor={borderColor}
      borderWidth="1px"
    >
      <CardBody>
        <VStack spacing={6} align="stretch">
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <Box
                p={2}
                borderRadius="lg"
                bg="purple.100"
                color="purple.600"
              >
                <Star size={20} />
              </Box>
              <VStack align="start" spacing={0}>
                <Text fontWeight="bold" fontSize="lg">
                  Smart Watchlist
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Track your favorite stocks
                </Text>
              </VStack>
            </HStack>
            <Badge colorScheme="purple" variant="outline">
              {watchlist.length} stocks
            </Badge>
          </HStack>

          {/* Add Symbol */}
          <HStack>
            <InputGroup>
              <InputLeftElement>
                <Search size={16} color="gray.400" />
              </InputLeftElement>
              <Input
                placeholder="Add symbol (e.g., AAPL, RELIANCE)"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
                bg={useColorModeValue('gray.50', 'gray.700')}
              />
            </InputGroup>
            <Button
              leftIcon={<Plus size={16} />}
              onClick={handleAddSymbol}
              colorScheme="purple"
              isDisabled={!newSymbol.trim()}
            >
              Add
            </Button>
          </HStack>

          {/* Watchlist Items */}
          <VStack spacing={3} align="stretch">
            {watchlist.map((item, index) => (
              <motion.div
                key={item.symbol}
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
                    borderColor: 'purple.300',
                    transform: 'translateY(-1px)',
                    boxShadow: 'md'
                  }}
                  transition="all 0.2s"
                >
                  <Flex justify="space-between" align="center">
                    <VStack align="start" spacing={1}>
                      <HStack>
                        <Text fontWeight="bold">
                          {item.symbol}
                        </Text>
                        {item.alert && (
                          <Badge colorScheme="orange" size="sm">
                            Alert
                          </Badge>
                        )}
                      </HStack>
                      <Text fontSize="lg" fontWeight="bold">
                        ₹{item.price.toFixed(2)}
                      </Text>
                      <HStack spacing={1}>
                        <TrendingUp 
                          size={12} 
                          color={item.change > 0 ? '#38A169' : '#E53E3E'} 
                        />
                        <Text
                          fontSize="sm"
                          color={item.change > 0 ? 'green.500' : 'red.500'}
                          fontWeight="medium"
                        >
                          {item.change > 0 ? '+' : ''}{item.change.toFixed(2)} 
                          ({item.changePercent > 0 ? '+' : ''}{item.changePercent.toFixed(2)}%)
                        </Text>
                      </HStack>
                    </VStack>

                    <VStack spacing={2}>
                      <Button
                        size="sm"
                        variant="outline"
                        colorScheme="blue"
                        onClick={() => handleAnalyze(item.symbol)}
                      >
                        Analyze
                      </Button>
                      <IconButton
                        size="sm"
                        variant="ghost"
                        colorScheme={item.alert ? 'orange' : 'gray'}
                        icon={<Bell size={16} />}
                        onClick={() => toggleAlert(item.symbol)}
                        aria-label="Toggle alert"
                      />
                    </VStack>
                  </Flex>
                </Box>
              </motion.div>
            ))}
          </VStack>

          {/* Quick Actions */}
          <HStack spacing={2}>
            <Button size="sm" variant="outline" flex={1}>
              View All
            </Button>
            <Button size="sm" variant="outline" flex={1}>
              Alerts
            </Button>
            <Button size="sm" variant="outline" flex={1}>
              Export
            </Button>
          </HStack>
        </VStack>
      </CardBody>
    </MotionCard>
  );
};

export default SmartWatchlist;
