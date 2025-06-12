import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  useColorModeValue,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Progress,
  List,
  ListItem,
  ListIcon,
  Tooltip,
  Button,
} from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Wifi, 
  WifiOff, 
  TrendingUp,
  CheckCircle,
  AlertTriangle,
  Clock,
  Zap
} from 'lucide-react';
import liveDataService from '../../services/liveDataService';

const MotionBox = motion(Box);

const LiveDataWidget = ({ 
  symbols = ['RELIANCE', 'TCS', 'INFY'],
  maxUpdates = 5,
  autoConnect = true,
  showStats = true,
  compact = false
}) => {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [liveUpdates, setLiveUpdates] = useState([]);
  const [stats, setStats] = useState({
    totalUpdates: 0,
    successfulAgents: 0,
    activeSymbols: 0
  });

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    if (!autoConnect) return;

    const initializeWidget = async () => {
      // Connect if not already connected
      if (!liveDataService.isConnected()) {
        await liveDataService.connect();
      }

      // Subscribe to data updates
      const unsubscribes = [
        liveDataService.subscribe('connection_status', handleConnectionStatus),
        liveDataService.subscribe('live_data', handleLiveData),
        liveDataService.subscribe('data_update', handleDataUpdate),
      ];

      // Subscribe to symbols if provided
      symbols.forEach(symbol => {
        liveDataService.subscribeToSymbol(symbol);
      });

      return () => {
        unsubscribes.forEach(unsubscribe => unsubscribe());
      };
    };

    initializeWidget();
  }, [autoConnect, symbols]);

  const handleConnectionStatus = (data) => {
    setConnectionStatus(data.status);
  };

  const handleLiveData = (data) => {
    setLiveUpdates(prev => {
      const newUpdate = {
        ...data,
        timestamp: Date.now(),
        id: `${data.symbol || 'system'}_${Date.now()}`
      };
      
      const updated = [newUpdate, ...prev];
      return updated.slice(0, maxUpdates);
    });

    // Update stats
    setStats(prev => ({
      totalUpdates: prev.totalUpdates + 1,
      successfulAgents: data.successful_agents?.length || 0,
      activeSymbols: new Set([...symbols, data.symbol]).size
    }));
  };

  const handleDataUpdate = (data) => {
    if (data.symbol && symbols.includes(data.symbol)) {
      setLiveUpdates(prev => {
        const newUpdate = {
          type: 'data_update',
          symbol: data.symbol,
          agent_count: data.agent_count,
          timestamp: Date.now(),
          id: `update_${data.symbol}_${Date.now()}`
        };
        
        const updated = [newUpdate, ...prev];
        return updated.slice(0, maxUpdates);
      });
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'green';
      case 'connecting': return 'blue';
      case 'disconnected': return 'gray';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected': return Wifi;
      case 'connecting': return Activity;
      case 'disconnected': return WifiOff;
      case 'error': return AlertTriangle;
      default: return WifiOff;
    }
  };

  const ConnectionIcon = getConnectionIcon();

  if (compact) {
    return (
      <Card bg={cardBg} size="sm" borderColor={borderColor} borderWidth="1px">
        <CardBody p={3}>
          <HStack justify="space-between">
            <HStack spacing={2}>
              <ConnectionIcon size={16} />
              <Text fontSize="sm" fontWeight="medium">Live Data</Text>
              <Badge size="sm" colorScheme={getConnectionStatusColor()}>
                {liveUpdates.length}
              </Badge>
            </HStack>
            <Badge 
              colorScheme={getConnectionStatusColor()} 
              variant="subtle"
              fontSize="xs"
            >
              {connectionStatus}
            </Badge>
          </HStack>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
      <CardHeader pb={2}>
        <HStack justify="space-between">
          <HStack spacing={2}>
            <Box p={2} borderRadius="md" bg="blue.100" color="blue.600">
              <Activity size={16} />
            </Box>
            <VStack align="start" spacing={0}>
              <Heading size="sm">Live Data Stream</Heading>
              <Text fontSize="xs" color="gray.500">
                Real-time stealth agent updates
              </Text>
            </VStack>
          </HStack>
          
          <Tooltip label={`Connection: ${connectionStatus}`}>
            <Badge 
              colorScheme={getConnectionStatusColor()} 
              variant="solid"
              cursor="pointer"
            >
              <HStack spacing={1}>
                <ConnectionIcon size={12} />
                <Text fontSize="xs">{connectionStatus}</Text>
              </HStack>
            </Badge>
          </Tooltip>
        </HStack>
      </CardHeader>

      <CardBody pt={0}>
        <VStack spacing={4} align="stretch">
          {/* Stats */}
          {showStats && (
            <HStack spacing={4} justify="space-around">
              <Stat size="sm" textAlign="center">
                <StatNumber fontSize="lg">{stats.totalUpdates}</StatNumber>
                <StatLabel fontSize="xs">Updates</StatLabel>
              </Stat>
              <Stat size="sm" textAlign="center">
                <StatNumber fontSize="lg">{stats.activeSymbols}</StatNumber>
                <StatLabel fontSize="xs">Symbols</StatLabel>
              </Stat>
              <Stat size="sm" textAlign="center">
                <StatNumber fontSize="lg">{stats.successfulAgents}</StatNumber>
                <StatLabel fontSize="xs">Agents</StatLabel>
              </Stat>
            </HStack>
          )}

          {/* Live Updates */}
          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" fontWeight="medium">Recent Updates</Text>
              {liveUpdates.length > 0 && (
                <Badge colorScheme="green" variant="outline" fontSize="xs">
                  <HStack spacing={1}>
                    <Activity size={8} />
                    <Text>LIVE</Text>
                  </HStack>
                </Badge>
              )}
            </HStack>

            {liveUpdates.length === 0 ? (
              <Box 
                p={4} 
                textAlign="center" 
                border="1px dashed" 
                borderColor={borderColor}
                borderRadius="md"
              >
                <Text fontSize="sm" color="gray.500">
                  Waiting for live data...
                </Text>
                {connectionStatus !== 'connected' && (
                  <Text fontSize="xs" color="gray.400" mt={1}>
                    Connect to start receiving updates
                  </Text>
                )}
              </Box>
            ) : (
              <VStack spacing={2} align="stretch" maxH="200px" overflowY="auto">
                <AnimatePresence>
                  {liveUpdates.map((update, index) => (
                    <MotionBox
                      key={update.id}
                      initial={{ opacity: 0, x: -20, scale: 0.95 }}
                      animate={{ opacity: 1, x: 0, scale: 1 }}
                      exit={{ opacity: 0, x: 20, scale: 0.95 }}
                      transition={{ duration: 0.3 }}
                      p={2}
                      border="1px"
                      borderColor={index === 0 ? 'blue.200' : borderColor}
                      borderRadius="md"
                      bg={index === 0 ? 'blue.50' : 'transparent'}
                    >
                      <HStack justify="space-between" fontSize="sm">
                        <VStack align="start" spacing={0}>
                          <HStack spacing={2}>
                            <Text fontWeight="medium">
                              {update.symbol || 'System'}
                            </Text>
                            {update.type === 'live_data' && (
                              <Badge size="sm" colorScheme="green">
                                {update.successful_agents?.length || 0} agents
                              </Badge>
                            )}
                            {update.type === 'data_update' && (
                              <Badge size="sm" colorScheme="blue">
                                {update.agent_count} updates
                              </Badge>
                            )}
                          </HStack>
                          <Text fontSize="xs" color="gray.500">
                            {new Date(update.timestamp).toLocaleTimeString()}
                          </Text>
                        </VStack>
                        
                        <ListIcon as={CheckCircle} color="green.400" />
                      </HStack>
                    </MotionBox>
                  ))}
                </AnimatePresence>
              </VStack>
            )}
          </Box>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default LiveDataWidget;
