import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Progress,
  useColorModeValue,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Button,
  Input,
  Select,
  Alert,
  AlertIcon,
  useToast,
  Flex,
  Divider,
  List,
  ListItem,
  ListIcon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
} from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Wifi, 
  WifiOff, 
  Play, 
  Square, 
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Database,
  Clock,
  CheckCircle,
  AlertTriangle,
  Zap
} from 'lucide-react';
import liveDataService from '../../services/liveDataService';

const MotionCard = motion(Card);
const MotionBox = motion(Box);

const LiveDataDashboard = () => {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [liveData, setLiveData] = useState([]);
  const [activeSessions, setActiveSessions] = useState({});
  const [availableAgents, setAvailableAgents] = useState({});
  const [performanceData, setPerformanceData] = useState(null);
  const [subscriptions, setSubscriptions] = useState(new Set());
  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE');
  const [sessionData, setSessionData] = useState({
    symbols: ['RELIANCE', 'TCS', 'INFY'],
    agents: ['enhanced_moneycontrol', 'moneycontrol', 'trendlyne'],
    interval: 30
  });
  const [isSessionRunning, setIsSessionRunning] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  const toast = useToast();
  const unsubscribeRefs = useRef([]);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const bgColor = useColorModeValue('gray.50', 'gray.900');

  // Initialize live data service
  useEffect(() => {
    const initializeService = async () => {
      // Connect to WebSocket
      await liveDataService.connect();

      // Subscribe to various data types
      const unsubscribes = [
        liveDataService.subscribe('connection_status', handleConnectionStatus),
        liveDataService.subscribe('live_data', handleLiveData),
        liveDataService.subscribe('data_update', handleDataUpdate),
        liveDataService.subscribe('performance_report', handlePerformanceData),
        liveDataService.subscribe('performance_update', handlePerformanceUpdate),
      ];

      unsubscribeRefs.current = unsubscribes;

      // Load initial data
      loadInitialData();
    };

    initializeService();

    return () => {
      // Cleanup subscriptions
      unsubscribeRefs.current.forEach(unsubscribe => unsubscribe());
      liveDataService.disconnect();
    };
  }, []);

  const handleConnectionStatus = (data) => {
    setConnectionStatus(data.status);
    
    if (data.status === 'connected') {
      toast({
        title: '🔗 Connected to Live Data Stream',
        status: 'success',
        duration: 3000,
      });
    } else if (data.status === 'disconnected') {
      toast({
        title: '🔌 Disconnected from Live Data Stream',
        status: 'warning',
        duration: 3000,
      });
    } else if (data.status === 'error') {
      toast({
        title: '❌ Live Data Connection Error',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleLiveData = (data) => {
    setLiveData(prevData => {
      const newData = [...prevData, { ...data, timestamp: Date.now() }];
      // Keep only last 50 updates
      return newData.slice(-50);
    });
  };

  const handleDataUpdate = (data) => {
    console.log('📊 Data update received:', data);
  };

  const handlePerformanceData = (data) => {
    setPerformanceData(data);
  };

  const handlePerformanceUpdate = (data) => {
    // Update real-time performance metrics
    if (performanceData) {
      setPerformanceData(prev => ({
        ...prev,
        system_health: data.system_health,
        agent_performance: data.agent_performance,
        last_update: data.timestamp
      }));
    }
  };

  const loadInitialData = async () => {
    try {
      const [sessionsResponse, agentsResponse] = await Promise.all([
        liveDataService.getSessionsList(),
        liveDataService.getAgentsList()
      ]);

      if (sessionsResponse.status === 'success') {
        setActiveSessions(sessionsResponse.active_sessions);
      }

      if (agentsResponse.status === 'success') {
        setAvailableAgents(agentsResponse.registered_agents);
      }

      // Get performance report
      liveDataService.getPerformanceReport();
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  const startCollectionSession = async () => {
    try {
      const response = await liveDataService.startCollectionSession({
        session_id: `live_session_${Date.now()}`,
        symbols: sessionData.symbols,
        agents: sessionData.agents,
        interval: sessionData.interval
      });

      if (response.status === 'success') {
        setIsSessionRunning(true);
        setCurrentSessionId(response.session_id);
        
        toast({
          title: '🚀 Collection Session Started',
          description: `Collecting data for ${sessionData.symbols.length} symbols`,
          status: 'success',
          duration: 3000,
        });

        // Subscribe to symbol updates
        sessionData.symbols.forEach(symbol => {
          liveDataService.subscribeToSymbol(symbol);
        });

        loadInitialData();
      }
    } catch (error) {
      toast({
        title: '❌ Failed to Start Session',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const stopCollectionSession = async () => {
    if (!currentSessionId) return;

    try {
      const response = await liveDataService.stopCollectionSession(currentSessionId);
      
      if (response.status === 'success') {
        setIsSessionRunning(false);
        setCurrentSessionId(null);
        
        toast({
          title: '⏹️ Collection Session Stopped',
          status: 'info',
          duration: 3000,
        });

        // Unsubscribe from symbol updates
        sessionData.symbols.forEach(symbol => {
          liveDataService.unsubscribeFromSymbol(symbol);
        });

        loadInitialData();
      }
    } catch (error) {
      toast({
        title: '❌ Failed to Stop Session',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const subscribeToSymbol = () => {
    if (selectedSymbol && !subscriptions.has(selectedSymbol)) {
      liveDataService.subscribeToSymbol(selectedSymbol);
      setSubscriptions(prev => new Set([...prev, selectedSymbol]));
      
      toast({
        title: `📡 Subscribed to ${selectedSymbol}`,
        status: 'success',
        duration: 2000,
      });
    }
  };

  const getConnectionStatusDisplay = () => {
    switch (connectionStatus) {
      case 'connected':
        return { icon: Wifi, color: 'green', text: 'Connected' };
      case 'connecting':
        return { icon: RefreshCw, color: 'blue', text: 'Connecting...' };
      case 'disconnected':
        return { icon: WifiOff, color: 'gray', text: 'Disconnected' };
      case 'error':
        return { icon: AlertTriangle, color: 'red', text: 'Error' };
      default:
        return { icon: WifiOff, color: 'gray', text: 'Unknown' };
    }
  };

  const connectionDisplay = getConnectionStatusDisplay();

  return (
    <Box bg={bgColor} minH="100vh" p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <MotionCard
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          bg={cardBg}
          borderColor={borderColor}
          borderWidth="1px"
        >
          <CardHeader>
            <HStack justify="space-between">
              <VStack align="start" spacing={1}>
                <Heading size="lg">Live Stealth Data Dashboard</Heading>
                <Text color="gray.500">Real-time monitoring of stealth agent collection</Text>
              </VStack>
              
              <HStack>
                <Badge 
                  colorScheme={connectionDisplay.color} 
                  variant="solid"
                  fontSize="sm"
                  p={2}
                >
                  <HStack spacing={2}>
                    <connectionDisplay.icon size={16} />
                    <Text>{connectionDisplay.text}</Text>
                  </HStack>
                </Badge>
                
                <Button
                  leftIcon={<RefreshCw size={16} />}
                  onClick={loadInitialData}
                  size="sm"
                  variant="outline"
                >
                  Refresh
                </Button>
              </HStack>
            </HStack>
          </CardHeader>
        </MotionCard>

        {/* Quick Stats */}
        <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={4}>
          <MotionCard
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            bg={cardBg}
          >
            <CardBody>
              <Stat>
                <StatLabel>Active Sessions</StatLabel>
                <StatNumber>{Object.keys(activeSessions).length}</StatNumber>
                <StatHelpText>Running collections</StatHelpText>
              </Stat>
            </CardBody>
          </MotionCard>

          <MotionCard
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            bg={cardBg}
          >
            <CardBody>
              <Stat>
                <StatLabel>Available Agents</StatLabel>
                <StatNumber>{Object.keys(availableAgents).length}</StatNumber>
                <StatHelpText>Registered scrapers</StatHelpText>
              </Stat>
            </CardBody>
          </MotionCard>

          <MotionCard
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            bg={cardBg}
          >
            <CardBody>
              <Stat>
                <StatLabel>Live Updates</StatLabel>
                <StatNumber>{liveData.length}</StatNumber>
                <StatHelpText>Data points received</StatHelpText>
              </Stat>
            </CardBody>
          </MotionCard>

          <MotionCard
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 }}
            bg={cardBg}
          >
            <CardBody>
              <Stat>
                <StatLabel>System Health</StatLabel>
                <StatNumber>{performanceData?.overall_health || 'N/A'}</StatNumber>
                <StatHelpText>Overall status</StatHelpText>
              </Stat>
            </CardBody>
          </MotionCard>
        </Grid>

        <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={6}>
          {/* Session Control */}
          <MotionCard
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
            bg={cardBg}
          >
            <CardHeader>
              <Heading size="md">Collection Session Control</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <HStack>
                  <Text fontWeight="medium" minW="100px">Symbols:</Text>
                  <Input
                    value={sessionData.symbols.join(', ')}
                    onChange={(e) => setSessionData(prev => ({
                      ...prev,
                      symbols: e.target.value.split(',').map(s => s.trim().toUpperCase())
                    }))}
                    placeholder="RELIANCE, TCS, INFY"
                  />
                </HStack>

                <HStack>
                  <Text fontWeight="medium" minW="100px">Interval (s):</Text>
                  <Input
                    type="number"
                    value={sessionData.interval}
                    onChange={(e) => setSessionData(prev => ({
                      ...prev,
                      interval: parseInt(e.target.value) || 30
                    }))}
                    min={10}
                    max={300}
                  />
                </HStack>

                <HStack>
                  <Button
                    leftIcon={isSessionRunning ? <Square size={16} /> : <Play size={16} />}
                    colorScheme={isSessionRunning ? 'red' : 'green'}
                    onClick={isSessionRunning ? stopCollectionSession : startCollectionSession}
                    isDisabled={connectionStatus !== 'connected'}
                    flex={1}
                  >
                    {isSessionRunning ? 'Stop Collection' : 'Start Collection'}
                  </Button>
                </HStack>

                {isSessionRunning && (
                  <Alert status="info" borderRadius="md">
                    <AlertIcon />
                    <VStack align="start" spacing={1}>
                      <Text fontWeight="medium">Session Active</Text>
                      <Text fontSize="sm">
                        Collecting data every {sessionData.interval}s for {sessionData.symbols.length} symbols
                      </Text>
                    </VStack>
                  </Alert>
                )}
              </VStack>
            </CardBody>
          </MotionCard>

          {/* Symbol Subscription */}
          <MotionCard
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
            bg={cardBg}
          >
            <CardHeader>
              <Heading size="md">Symbol Subscriptions</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <HStack>
                  <Input
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value.toUpperCase())}
                    placeholder="Enter symbol (e.g., RELIANCE)"
                  />
                  <Button
                    onClick={subscribeToSymbol}
                    colorScheme="blue"
                    isDisabled={connectionStatus !== 'connected'}
                  >
                    Subscribe
                  </Button>
                </HStack>

                <Box>
                  <Text fontWeight="medium" mb={2}>Active Subscriptions:</Text>
                  <List spacing={1}>
                    {Array.from(subscriptions).map(symbol => (
                      <ListItem key={symbol}>
                        <ListIcon as={CheckCircle} color="green.500" />
                        {symbol}
                      </ListItem>
                    ))}
                  </List>
                </Box>
              </VStack>
            </CardBody>
          </MotionCard>
        </Grid>

        {/* Live Data Feed */}
        <MotionCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          bg={cardBg}
        >
          <CardHeader>
            <HStack justify="space-between">
              <Heading size="md">Live Data Feed</Heading>
              <Badge colorScheme="green" variant="outline">
                <HStack spacing={1}>
                  <Activity size={12} />
                  <Text>LIVE</Text>
                </HStack>
              </Badge>
            </HStack>
          </CardHeader>
          <CardBody>
            {liveData.length === 0 ? (
              <Text color="gray.500" textAlign="center" py={8}>
                No live data received yet. Start a collection session to see real-time updates.
              </Text>
            ) : (
              <VStack spacing={3} align="stretch" maxH="400px" overflowY="auto">
                <AnimatePresence>
                  {liveData.slice(-10).reverse().map((data, index) => (
                    <MotionBox
                      key={data.timestamp}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      p={3}
                      border="1px"
                      borderColor={borderColor}
                      borderRadius="md"
                      bg={index === 0 ? 'blue.50' : 'transparent'}
                    >
                      <HStack justify="space-between">
                        <VStack align="start" spacing={1}>
                          <Text fontWeight="medium">
                            {data.symbol || 'System Update'}
                          </Text>
                          <Text fontSize="sm" color="gray.500">
                            {data.successful_agents?.length || 0} agents successful
                          </Text>
                        </VStack>
                        <VStack align="end" spacing={1}>
                          <Badge colorScheme="blue" variant="subtle">
                            {new Date(data.timestamp).toLocaleTimeString()}
                          </Badge>
                          <Text fontSize="xs" color="gray.500">
                            Session: {data.session_id?.substring(0, 8)}...
                          </Text>
                        </VStack>
                      </HStack>
                    </MotionBox>
                  ))}
                </AnimatePresence>
              </VStack>
            )}
          </CardBody>
        </MotionCard>

        {/* Agent Performance */}
        {Object.keys(availableAgents).length > 0 && (
          <MotionCard
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            bg={cardBg}
          >
            <CardHeader>
              <Heading size="md">Agent Performance</Heading>
            </CardHeader>
            <CardBody>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Agent</Th>
                    <Th isNumeric>Success Rate</Th>
                    <Th isNumeric>Avg Response Time</Th>
                    <Th isNumeric>Total Executions</Th>
                    <Th>Last Execution</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {Object.entries(availableAgents).map(([agentName, metrics]) => (
                    <Tr key={agentName}>
                      <Td fontWeight="medium">{agentName}</Td>
                      <Td isNumeric>
                        <Badge 
                          colorScheme={parseFloat(metrics.success_rate) > 80 ? 'green' : 'yellow'}
                        >
                          {metrics.success_rate}
                        </Badge>
                      </Td>
                      <Td isNumeric>{metrics.avg_execution_time}</Td>
                      <Td isNumeric>{metrics.total_executions}</Td>
                      <Td fontSize="sm" color="gray.500">
                        {metrics.last_execution ? 
                          new Date(metrics.last_execution).toLocaleString() : 
                          'Never'
                        }
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </CardBody>
          </MotionCard>
        )}
      </VStack>
    </Box>
  );
};

export default LiveDataDashboard;
