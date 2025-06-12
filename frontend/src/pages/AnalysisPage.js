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
// Import new components
import AnimatedBackground from '../components/common/AnimatedBackground';
import RealTimeAnalysisStream from '../components/analysis/RealTimeAnalysisStream';

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
    <AnimatedBackground>
      <VStack spacing={8} align="stretch" p={6}>
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2} color={useColorModeValue('gray.800', 'white')}>
            Stock Analysis
          </Heading>
          <Text color={useColorModeValue('gray.600', 'gray.300')}>
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
          boxShadow="xl"
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
                    _focus={{ borderColor: 'brand.500', boxShadow: '0 0 0 1px var(--chakra-colors-brand-500)' }}
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
                  boxShadow="lg"
                  _hover={{ transform: 'translateY(-2px)', boxShadow: 'xl' }}
                  transition="all 0.2s"
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
                boxShadow="lg"
                _hover={{ 
                  transform: 'translateY(-4px)', 
                  boxShadow: 'xl',
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

        {/* Real-Time Analysis Stream */}
        {isAnalyzing && analysisSymbol && (
          <RealTimeAnalysisStream symbol={analysisSymbol} analysisData={isAnalyzing} />
        )}

        {/* Analysis Results */}
        {analysisSymbol && !isAnalyzing && analysisData && (
          <VStack spacing={6} align="stretch">
            {/* Main Analysis Results */}
            <AnalysisResults data={analysisData} symbol={analysisSymbol} />

            {/* Detailed Analysis Tabs */}
            <Tabs variant="enclosed" colorScheme="brand">
              <TabList>
                <Tab>Agent Breakdown</Tab>
                <Tab>Technical Chart</Tab>
                <Tab>Risk Assessment</Tab>
                <Tab>Market Context</Tab>
              </TabList>

              <TabPanels>
                <TabPanel p={0} pt={6}>
                  <AgentBreakdown data={analysisData} symbol={analysisSymbol} />
                </TabPanel>
                <TabPanel p={0} pt={6}>
                  <TechnicalChart technicalData={analysisData?.technical} />
                </TabPanel>
                <TabPanel p={0} pt={6}>
                  <RiskAssessment riskData={analysisData?.risk} />
                </TabPanel>
                <TabPanel p={0} pt={6}>
                  <Box>
                    <Text>Market context analysis coming soon...</Text>
                  </Box>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </VStack>
        )}

        {/* Error Handling */}
        {analysisError && (
          <Alert status="error" borderRadius="lg" boxShadow="lg">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              <Text fontWeight="medium">Analysis failed</Text>
              <Text fontSize="sm">{analysisError.message}</Text>
            </VStack>
          </Alert>
        )}
      </VStack>
    </AnimatedBackground>
  );
};

export default AnalysisPage;
