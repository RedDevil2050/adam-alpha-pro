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
  Badge,
  useColorModeValue,
  Container,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { 
  Search, 
  Activity,
  BarChart3, 
  Database,
  Eye
} from 'lucide-react';
import { useQuery } from 'react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import apiService from '../services/api';

// Import the new comprehensive dashboard components
import LiveDataDashboard from '../components/dashboard/LiveDataDashboard';
import MarketOverviewCard from '../components/dashboard/MarketOverviewCard';
import QuickAnalysisCard from '../components/dashboard/QuickAnalysisCard';
import RecentAnalyses from '../components/dashboard/RecentAnalyses';
import SystemHealthCard from '../components/dashboard/SystemHealthCard';
import IndianMarketDashboard from '../components/dashboard/IndianMarketDashboard';

// Import other components
import AnimatedBackground from '../components/common/AnimatedBackground';
import SystemHealthWidget from '../components/widgets/SystemHealthWidget';
import SmartWatchlist from '../components/widgets/SmartWatchlist';
import FloatingActionButton from '../components/common/FloatingActionButton';

const DashboardPage = () => {
  const [searchSymbol, setSearchSymbol] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const navigate = useNavigate();
  
  const bg = useColorModeValue('gray.50', 'gray.900');
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

  return (
    <Box bg={bg} minH="100vh">
      <AnimatedBackground />
      
      <Container maxW="full" py={6}>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <VStack spacing={6} align="stretch" mb={8}>
            <HStack justify="space-between" align="center" wrap="wrap" spacing={4}>
              <VStack align="start" spacing={1}>
                <Heading size="xl" bgGradient="linear(to-r, blue.400, purple.500)" bgClip="text">
                  🇮🇳 Zion Market Intelligence
                </Heading>
                <Text color="gray.600" fontSize="lg">
                  Live Indian equity market analysis powered by AI agents
                </Text>
              </VStack>
              
              {/* Quick Search */}
              <Box w={{ base: 'full', md: '300px' }}>
                <form onSubmit={handleSearch}>
                  <InputGroup size="lg">
                    <Input
                      placeholder="Search stocks (e.g., RELIANCE, TCS)"
                      value={searchSymbol}
                      onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
                      bg={cardBg}
                      border="2px"
                      borderColor={borderColor}
                      _focus={{ borderColor: 'blue.400' }}
                    />
                    <InputRightElement>
                      <Button type="submit" colorScheme="blue" size="sm" mr={1}>
                        <Search size={16} />
                      </Button>
                    </InputRightElement>
                  </InputGroup>
                </form>
              </Box>
            </HStack>
          </VStack>
        </motion.div>

        {/* Main Dashboard Tabs */}
        <Tabs 
          index={activeTab} 
          onChange={setActiveTab}
          variant="enclosed"
          colorScheme="blue"
        >
          <TabList mb={6} bg={cardBg} borderRadius="lg" p={2}>
            <Tab leftIcon={<Activity />}>Live Data Dashboard</Tab>
            <Tab leftIcon={<BarChart3 />}>Indian Market Overview</Tab>
            <Tab leftIcon={<Database />}>Analysis Tools</Tab>
            <Tab leftIcon={<Eye />}>Stealth Agents</Tab>
          </TabList>

          <TabPanels>
            {/* Live Data Dashboard Tab */}
            <TabPanel p={0}>
              <LiveDataDashboard />
            </TabPanel>

            {/* Indian Market Overview Tab */}
            <TabPanel p={0}>
              <IndianMarketDashboard />
            </TabPanel>

            {/* Analysis Tools Tab */}
            <TabPanel p={0}>
              <Grid templateColumns="repeat(12, 1fr)" gap={6}>
                <Box gridColumn="span 8">
                  <VStack spacing={6}>
                    <QuickAnalysisCard />
                    <RecentAnalyses />
                  </VStack>
                </Box>
                <Box gridColumn="span 4">
                  <VStack spacing={6}>
                    <SystemHealthCard healthData={healthData} />
                    <SmartWatchlist />
                    <SystemHealthWidget />
                  </VStack>
                </Box>
              </Grid>
            </TabPanel>

            {/* Stealth Agents Tab */}
            <TabPanel p={0}>
              <StealthAgentsDashboard />
            </TabPanel>
          </TabPanels>
        </Tabs>

        {/* Floating Action Button */}
        <FloatingActionButton />
      </Container>
    </Box>
  );
};

// New Stealth Agents Dashboard Component
const StealthAgentsDashboard = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Grid templateColumns="repeat(12, 1fr)" gap={6}>
      <Card
        gridColumn="span 12"
        bg={cardBg}
        border="1px"
        borderColor={borderColor}
      >
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Heading size="lg" display="flex" alignItems="center" gap={2}>
              <Eye size={24} color="#D69E2E" />
              Stealth Data Collection Agents
            </Heading>
            
            <Text color="gray.600">
              Monitor the performance and status of our data collection agents across multiple platforms
            </Text>

            <Grid templateColumns="repeat(auto-fit, minmax(300px, 1fr))" gap={4}>
              <AgentStatusCard 
                name="MoneyControl Agent"
                status="active"
                dataPoints={1247}
                successRate={98.5}
                lastUpdate="2 minutes ago"
                description="Real-time stock prices and company data"
              />
              <AgentStatusCard 
                name="TrendLyne Agent"
                status="active"
                dataPoints={892}
                successRate={96.2}
                lastUpdate="3 minutes ago"
                description="Technical analysis and quality scores"
              />
              <AgentStatusCard 
                name="Screener Agent"
                status="active"
                dataPoints={2156}
                successRate={99.1}
                lastUpdate="1 minute ago"
                description="Fundamental ratios and financial metrics"
              />
              <AgentStatusCard 
                name="StockEdge Agent"
                status="active"
                dataPoints={743}
                successRate={94.8}
                lastUpdate="4 minutes ago"
                description="Market insights and sector analysis"
              />
            </Grid>
          </VStack>
        </CardBody>
      </Card>
    </Grid>
  );
};

// Agent Status Card Component
const AgentStatusCard = ({ name, status, dataPoints, successRate, lastUpdate, description }) => {
  const cardBg = useColorModeValue('gray.50', 'gray.700');
  const statusColor = status === 'active' ? 'green' : 'red';

  return (
    <Card bg={cardBg} border="1px" borderColor="gray.200">
      <CardBody>
        <VStack spacing={4} align="stretch">
          <HStack justify="space-between">
            <Text fontWeight="bold" fontSize="lg">{name}</Text>
            <Badge colorScheme={statusColor} variant="solid">
              {status.toUpperCase()}
            </Badge>
          </HStack>
          
          <Text fontSize="sm" color="gray.600">
            {description}
          </Text>
          
          <VStack spacing={2} align="stretch">
            <HStack justify="space-between">
              <Text fontSize="sm">Data Points:</Text>
              <Text fontWeight="bold">{dataPoints.toLocaleString()}</Text>
            </HStack>
            <HStack justify="space-between">
              <Text fontSize="sm">Success Rate:</Text>
              <Text fontWeight="bold" color="green.500">{successRate}%</Text>
            </HStack>
            <HStack justify="space-between">
              <Text fontSize="sm">Last Update:</Text>
              <Text fontSize="sm" color="gray.500">{lastUpdate}</Text>
            </HStack>
          </VStack>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default DashboardPage;
