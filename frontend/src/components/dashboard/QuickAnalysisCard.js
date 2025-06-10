import React, { useState } from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Input,
  Grid,
  Badge,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { Zap, BarChart3, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const MotionBox = motion(Box);

const QuickAnalysisCard = () => {
  const [symbol, setSymbol] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const navigate = useNavigate();
  
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const popularSymbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'];

  const handleQuickAnalysis = async (symbolToAnalyze) => {
    setIsAnalyzing(true);
    // Simulate API call delay
    setTimeout(() => {
      navigate(`/analysis/${symbolToAnalyze}`);
      setIsAnalyzing(false);
    }, 500);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (symbol.trim()) {
      handleQuickAnalysis(symbol.toUpperCase());
      setSymbol('');
    }
  };

  return (
    <MotionBox
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardHeader>
          <HStack>
            <Box p={2} borderRadius="lg" bg="brand.100" color="brand.600">
              <Zap size={20} />
            </Box>
            <Heading size="md">Quick Analysis</Heading>
          </HStack>
        </CardHeader>
        <CardBody pt={0}>
          <VStack spacing={6} align="stretch">
            {/* Custom Symbol Input */}
            <form onSubmit={handleSubmit}>
              <VStack spacing={3}>
                <Input
                  placeholder="Enter symbol for instant analysis"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  size="lg"
                  bg={useColorModeValue('gray.50', 'gray.700')}
                />
                <Button
                  type="submit"
                  colorScheme="brand"
                  size="lg"
                  w="full"
                  leftIcon={<BarChart3 size={18} />}
                  isLoading={isAnalyzing}
                  loadingText="Analyzing..."
                  isDisabled={!symbol.trim()}
                >
                  Analyze Now
                </Button>
              </VStack>
            </form>

            {/* Popular Symbols */}
            <Box>
              <Text fontSize="sm" color="gray.500" mb={3}>
                Popular Symbols
              </Text>
              <Grid templateColumns="repeat(3, 1fr)" gap={2}>
                {popularSymbols.map((sym) => (
                  <Button
                    key={sym}
                    variant="outline"
                    size="sm"
                    onClick={() => handleQuickAnalysis(sym)}
                    isLoading={isAnalyzing}
                    _hover={{
                      borderColor: 'brand.400',
                      color: 'brand.500',
                    }}
                  >
                    {sym}
                  </Button>
                ))}
              </Grid>
            </Box>

            {/* Analysis Features */}
            <Box>
              <Text fontSize="sm" color="gray.500" mb={3}>
                Analysis Includes
              </Text>
              <VStack spacing={2} align="start">
                <HStack spacing={2}>
                  <Badge colorScheme="blue" variant="subtle">Technical</Badge>
                  <Text fontSize="sm">RSI, MACD, Momentum</Text>
                </HStack>
                <HStack spacing={2}>
                  <Badge colorScheme="green" variant="subtle">Fundamental</Badge>
                  <Text fontSize="sm">P/E, EPS, Valuation</Text>
                </HStack>
                <HStack spacing={2}>
                  <Badge colorScheme="purple" variant="subtle">Sentiment</Badge>
                  <Text fontSize="sm">News, Social, ESG</Text>
                </HStack>
                <HStack spacing={2}>
                  <Badge colorScheme="orange" variant="subtle">Risk</Badge>
                  <Text fontSize="sm">Volatility, Beta, VaR</Text>
                </HStack>
              </VStack>
            </Box>
          </VStack>
        </CardBody>
      </Card>
    </MotionBox>
  );
};

export default QuickAnalysisCard;
