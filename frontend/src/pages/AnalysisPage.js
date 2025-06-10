import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  CardHeader,
  Button,
  Input,
  InputGroup,
  InputRightElement,
  Badge,
  Progress,
  Spinner,
  Alert,
  AlertIcon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useColorModeValue,
  Flex,
  Divider,
} from '@chakra-ui/react';
import { 
  Search, 
  BarChart3, 
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Zap,
  Brain,
  Shield,
  Briefcase,
} from 'lucide-react';
import { useQuery } from 'react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import apiService from '../services/api';
import AnalysisResults from '../components/analysis/AnalysisResults';
import AgentBreakdown from '../components/analysis/AgentBreakdown';
import TechnicalChart from '../components/analysis/TechnicalChart';
import RiskAssessment from '../components/analysis/RiskAssessment';

const MotionCard = motion(Card);

const AnalysisPage = () => {
  const { symbol: urlSymbol } = useParams();
  const [symbol, setSymbol] = useState(urlSymbol || '');
  const [analysisSymbol, setAnalysisSymbol] = useState(urlSymbol || '');
  const [isValidatingSymbol, setIsValidatingSymbol] = useState(false);
  const navigate = useNavigate();
  
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Fetch analysis data
  const { 
    data: analysisData, 
    isLoading: isAnalyzing, 
    error: analysisError,
    refetch: refetchAnalysis 
  } = useQuery(
    ['analysis', analysisSymbol],
    () => apiService.analyzeStock(analysisSymbol),
    {
      enabled: !!analysisSymbol,
      retry: 1,
      onError: (error) => {
        toast.error(`Analysis failed: ${error.response?.data?.detail || error.message}`);
      }
    }
  );

  // Update URL when symbol changes
  useEffect(() => {
    if (urlSymbol && urlSymbol !== symbol) {
      setSymbol(urlSymbol);
      setAnalysisSymbol(urlSymbol);
    }
  }, [urlSymbol]);

  const handleSymbolSubmit = async (e) => {
    e.preventDefault();
    if (!symbol.trim()) return;

    const upperSymbol = symbol.toUpperCase();
    setIsValidatingSymbol(true);

    try {
      // Validate symbol first
      await apiService.validateSymbol(upperSymbol);
      setAnalysisSymbol(upperSymbol);
      navigate(`/analysis/${upperSymbol}`);
      toast.success(`Starting analysis for ${upperSymbol}`);
    } catch (error) {
      toast.error(`Invalid symbol: ${error.response?.data?.detail || 'Symbol not found'}`);
    } finally {
      setIsValidatingSymbol(false);
    }
  };

  const analysisCategories = [
    { 
      id: 'technical', 
      name: 'Technical', 
      icon: BarChart3, 
      color: 'blue',
      description: 'RSI, MACD, Moving Averages, Momentum'
    },
    { 
      id: 'fundamental', 
      name: 'Fundamental', 
      icon: Target, 
      color: 'green',
      description: 'P/E Ratio, EPS, Financial Health'
    },
    { 
      id: 'sentiment', 
      name: 'Sentiment', 
      icon: Brain, 
      color: 'purple',
      description: 'News Analysis, Social Media, ESG'
    },
    { 
      id: 'risk', 
      name: 'Risk', 
      icon: Shield, 
      color: 'orange',
      description: 'Volatility, VaR, Beta Analysis'
    },
  ];

  return (
    <VStack spacing={8} align="stretch">
      {/* Header */}
      <Box>
        <Heading size="lg" mb={2}>
          Stock Analysis
        </Heading>
        <Text color="gray.500">
          Comprehensive market analysis powered by AI agents
        </Text>
      </Box>

      {/* Symbol Search */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        bg={cardBg}
        borderColor={borderColor}
        borderWidth="1px"
      >
        <CardBody>
          <form onSubmit={handleSymbolSubmit}>
            <HStack spacing={4}>
              <InputGroup size="lg" flex={1}>
                <Input
                  placeholder="Enter stock symbol (e.g., AAPL, TSLA, RELIANCE.NS)"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  bg={useColorModeValue('gray.50', 'gray.700')}
                  border="1px"
                  borderColor={useColorModeValue('gray.300', 'gray.600')}
                  _hover={{ borderColor: 'brand.400' }}
                  _focus={{ borderColor: 'brand.500' }}
                />
                <InputRightElement>
                  <Search size={20} color="gray.400" />
                </InputRightElement>
              </InputGroup>
              <Button
                type="submit"
                colorScheme="brand"
                size="lg"
                leftIcon={<BarChart3 size={20} />}
                isLoading={isValidatingSymbol || isAnalyzing}
                loadingText="Analyzing..."
                isDisabled={!symbol.trim()}
              >
                Analyze
              </Button>
            </HStack>
          </form>
        </CardBody>
      </MotionCard>

      {/* Analysis Categories Overview */}
      {!analysisSymbol && (
        <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={6}>
          {analysisCategories.map((category, index) => (
            <MotionCard
              key={category.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              bg={cardBg}
              borderColor={borderColor}
              borderWidth="1px"
              _hover={{ 
                transform: 'translateY(-4px)', 
                boxShadow: 'lg',
                borderColor: `${category.color}.300`
              }}
              cursor="pointer"
            >
              <CardBody>
                <VStack spacing={4}>
                  <Box
                    p={4}
                    borderRadius="xl"
                    bg={`${category.color}.100`}
                    color={`${category.color}.600`}
                  >
                    <category.icon size={32} />
                  </Box>
                  <VStack spacing={2}>
                    <Heading size="md" textAlign="center">
                      {category.name}
                    </Heading>
                    <Text fontSize="sm" color="gray.500" textAlign="center">
                      {category.description}
                    </Text>
                  </VStack>
                </VStack>
              </CardBody>
            </MotionCard>
          ))}
        </Grid>
      )}

      {/* Analysis Results */}
      {analysisSymbol && (
        <>
          {isAnalyzing && (
            <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
              <CardBody>
                <VStack spacing={6}>
                  <VStack spacing={4}>
                    <Spinner size="xl" color="brand.500" thickness="4px" />
                    <Heading size="md">Analyzing {analysisSymbol}</Heading>
                    <Text color="gray.500" textAlign="center">
                      Running comprehensive analysis across multiple AI agents...
                    </Text>
                  </VStack>
                  
                  <Box w="full" maxW="md">
                    <Progress 
                      size="lg" 
                      colorScheme="brand" 
                      isIndeterminate 
                      borderRadius="full"
                    />
                  </Box>

                  <Grid templateColumns="repeat(2, 1fr)" gap={4} w="full" maxW="md">
                    {analysisCategories.map((category) => (
                      <HStack key={category.id} spacing={2}>
                        <Box
                          p={1}
                          borderRadius="md"
                          bg={`${category.color}.100`}
                          color={`${category.color}.600`}
                        >
                          <category.icon size={16} />
                        </Box>
                        <Text fontSize="sm">{category.name} Agents</Text>
                      </HStack>
                    ))}
                  </Grid>
                </VStack>
              </CardBody>
            </Card>
          )}

          {analysisError && (
            <Alert status="error" borderRadius="lg">
              <AlertIcon />
              <VStack align="start" spacing={1}>
                <Text fontWeight="medium">Analysis Failed</Text>
                <Text fontSize="sm">
                  {analysisError.response?.data?.detail || analysisError.message}
                </Text>
              </VStack>
            </Alert>
          )}

          {analysisData && !isAnalyzing && (
            <Tabs colorScheme="brand" variant="enclosed">
              <TabList>
                <Tab>Overview</Tab>
                <Tab>Technical</Tab>
                <Tab>Agents</Tab>
                <Tab>Risk</Tab>
              </TabList>

              <TabPanels>
                <TabPanel px={0}>
                  <AnalysisResults data={analysisData} symbol={analysisSymbol} />
                </TabPanel>
                <TabPanel px={0}>
                  <TechnicalChart symbol={analysisSymbol} data={analysisData} />
                </TabPanel>
                <TabPanel px={0}>
                  <AgentBreakdown data={analysisData} symbol={analysisSymbol} />
                </TabPanel>
                <TabPanel px={0}>
                  <RiskAssessment data={analysisData} symbol={analysisSymbol} />
                </TabPanel>
              </TabPanels>
            </Tabs>
          )}
        </>
      )}
    </VStack>
  );
};

export default AnalysisPage;
