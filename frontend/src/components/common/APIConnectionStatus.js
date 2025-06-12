import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Progress,
  useColorModeValue,
  Card,
  CardBody,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Wifi, WifiOff, Activity, AlertCircle, CheckCircle } from 'lucide-react';

const MotionCard = motion(Card);

const APIConnectionStatus = ({ apiUrl = 'http://localhost:8000' }) => {
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [responseTime, setResponseTime] = useState(0);
  const [lastCheck, setLastCheck] = useState(new Date());

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    const checkConnection = async () => {
      const startTime = Date.now();
      try {
        const response = await fetch(`${apiUrl}/api/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        const endTime = Date.now();
        const timeTaken = endTime - startTime;
        
        if (response.ok) {
          setConnectionStatus('connected');
          setResponseTime(timeTaken);
        } else {
          setConnectionStatus('error');
        }
      } catch (error) {
        setConnectionStatus('disconnected');
        setResponseTime(0);
      }
      
      setLastCheck(new Date());
    };

    // Initial check
    checkConnection();

    // Set up interval for periodic checks
    const interval = setInterval(checkConnection, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [apiUrl]);

  const getStatusInfo = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          icon: CheckCircle,
          color: 'green',
          label: 'Connected',
          description: 'API is healthy and responsive'
        };
      case 'connecting':
        return {
          icon: Activity,
          color: 'blue',
          label: 'Connecting',
          description: 'Establishing connection to API...'
        };
      case 'error':
        return {
          icon: AlertCircle,
          color: 'orange',
          label: 'Warning',
          description: 'API responded with errors'
        };
      case 'disconnected':
      default:
        return {
          icon: WifiOff,
          color: 'red',
          label: 'Disconnected',
          description: 'Unable to reach API server'
        };
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  return (
    <MotionCard
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      bg={cardBg}
      borderColor={borderColor}
      borderWidth="1px"
      size="sm"
    >
      <CardBody p={3}>
        <HStack spacing={3} justify="space-between">
          <HStack spacing={3}>
            <motion.div
              animate={connectionStatus === 'connecting' ? {
                rotate: 360,
                transition: { duration: 2, repeat: Infinity, ease: "linear" }
              } : {}}
            >
              <Box
                p={2}
                borderRadius="md"
                bg={`${statusInfo.color}.100`}
                color={`${statusInfo.color}.600`}
              >
                <StatusIcon size={16} />
              </Box>
            </motion.div>
            
            <VStack spacing={0} align="start">
              <HStack spacing={2}>
                <Text fontSize="sm" fontWeight="medium">
                  API Status
                </Text>
                <Badge 
                  colorScheme={statusInfo.color} 
                  variant="subtle" 
                  fontSize="xs"
                >
                  {statusInfo.label}
                </Badge>
              </HStack>
              <Text fontSize="xs" color="gray.500">
                {statusInfo.description}
              </Text>
            </VStack>
          </HStack>

          <VStack spacing={1} align="end">
            {connectionStatus === 'connected' && (
              <>
                <Text fontSize="xs" fontWeight="medium" color="green.600">
                  {responseTime}ms
                </Text>
                <Progress
                  value={Math.max(0, 100 - (responseTime / 10))}
                  size="xs"
                  colorScheme="green"
                  w="40px"
                  borderRadius="full"
                />
              </>
            )}
            <Text fontSize="xs" color="gray.400">
              {lastCheck.toLocaleTimeString()}
            </Text>
          </VStack>
        </HStack>
      </CardBody>
    </MotionCard>
  );
};

export default APIConnectionStatus;
