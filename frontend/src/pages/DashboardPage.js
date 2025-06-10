import React, { useState } from 'react';
import {
  Box,
  Grid,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  Button,
  Input,
  InputGroup,
  InputRightElement,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Badge,
  Flex,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Target,
  Zap,
  Clock,
  Activity
} from 'lucide-react';
import { useQuery } from 'react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import apiService from '../services/api';
import MarketOverviewCard from '../components/dashboard/MarketOverviewCard';
import QuickAnalysisCard from '../components/dashboard/QuickAnalysisCard';
import RecentAnalyses from '../components/dashboard/RecentAnalyses';
import SystemHealthCard from '../components/dashboard/SystemHealthCard';

const MotionCard = motion(Card);

const DashboardPage = () => {
  const [searchSymbol, setSearchSymbol] = useState('');
  const navigate = useNavigate();
  
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Fetch market state
  const { data: marketData, isLoading: marketLoading, error: marketError } = useQuery(
    'marketState',
    apiService.getMarketState,
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: 2,
    }
  );

  // Fetch system health
  const { data: healthData, isLoading: healthLoading } = useQuery(
    'systemHealth',
    apiService.getHealth,
    {
      refetchInterval: 60000, // Refresh every minute
      retry: 1,
    }
  );

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchSymbol.trim()) {
      navigate(`/analysis/${searchSymbol.toUpperCase()}`);
      setSearchSymbol('');
    }
  };

  const quickStats = [
    {
      label: 'Analyses Today',
      value: '127',
      change: 12.5,
      icon: BarChart3,
      color: 'blue',
    },
    {
      label: 'Active Agents',
      value: '23',
      change: 0,
      icon: Zap,
      color: 'green',
    },
    {
      label: 'Avg Response Time',
      value: '1.2s',
      change: -8.3,
      icon: Clock,
      color: 'purple',
    },
    {
      label: 'Success Rate',
      value: '99.1%',
      change: 2.1,
      icon: Target,
      color: 'orange',
    },
  ];

  return (
    <VStack spacing={8} align="stretch">
      {/* Header Section */}
      <Box>
        <Heading size="lg" mb={2}>
          Market Analysis Dashboard
        </Heading>
        <Text color="gray.500">
          Real-time insights powered by advanced AI agents
        </Text>
      </Box>

      {/* Quick Search */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        bg={cardBg}
        borderColor={borderColor}
        borderWidth="1px"
      >
        <CardBody>
          <form onSubmit={handleSearch}>
            <HStack spacing={4}>
              <InputGroup size="lg" flex={1}>
                <Input
                  placeholder="Enter stock symbol (e.g., AAPL, TSLA, MSFT)"
                  value={searchSymbol}
                  onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
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
                isDisabled={!searchSymbol.trim()}
              >
                Analyze
              </Button>
            </HStack>
          </form>
        </CardBody>
      </MotionCard>

      {/* Quick Stats Grid */}
      <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={6}>
        {quickStats.map((stat, index) => (
          <MotionCard
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            bg={cardBg}
            borderColor={borderColor}
            borderWidth="1px"
            _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
            cursor="pointer"
          >
            <CardBody>
              <Stat>
                <Flex justify="space-between" align="start">
                  <Box>
                    <StatLabel fontSize="sm" color="gray.500">
                      {stat.label}
                    </StatLabel>
                    <StatNumber fontSize="2xl" fontWeight="bold">
                      {stat.value}
                    </StatNumber>
                    {stat.change !== 0 && (
                      <StatHelpText mb={0}>
                        <StatArrow type={stat.change > 0 ? 'increase' : 'decrease'} />
                        {Math.abs(stat.change)}%
                      </StatHelpText>
                    )}
                  </Box>
                  <Box
                    p={3}
                    borderRadius="lg"
                    bg={`${stat.color}.100`}
                    color={`${stat.color}.600`}
                  >
                    <stat.icon size={24} />
                  </Box>
                </Flex>
              </Stat>
            </CardBody>
          </MotionCard>
        ))}
      </Grid>

      {/* Main Content Grid */}
      <Grid templateColumns={{ base: '1fr', lg: '2fr 1fr' }} gap={8}>
        {/* Left Column */}
        <VStack spacing={6} align="stretch">
          {/* Market Overview */}
          <MarketOverviewCard data={marketData} isLoading={marketLoading} error={marketError} />
          
          {/* Quick Analysis */}
          <QuickAnalysisCard />
        </VStack>

        {/* Right Column */}
        <VStack spacing={6} align="stretch">
          {/* System Health */}
          <SystemHealthCard data={healthData} isLoading={healthLoading} />
          
          {/* Recent Analyses */}
          <RecentAnalyses />
        </VStack>
      </Grid>

      {/* Error Handling */}
      {marketError && (
        <Alert status="warning" borderRadius="lg">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="medium">Market data temporarily unavailable</Text>
            <Text fontSize="sm">Some features may be limited until connection is restored.</Text>
          </VStack>
        </Alert>
      )}
    </VStack>
  );
};

export default DashboardPage;
