import React from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  Progress,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
} from '@chakra-ui/react';
import { Activity, Server, Database, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

const SystemHealthCard = ({ data, isLoading }) => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  if (isLoading) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardBody>
          <VStack spacing={4}>
            <Spinner size="md" color="brand.500" />
            <Text fontSize="sm">Checking system health...</Text>
          </VStack>
        </CardBody>
      </Card>
    );
  }

  // Mock health data if not available
  const mockHealthData = {
    status: 'healthy',
    details: {
      system: {
        cpu_usage: 45.2,
        memory_usage: 68.7,
      },
      components: {
        redis: 'healthy',
        database: 'healthy',
        api: 'healthy',
      },
      uptime: '5d 14h 32m',
      response_time: '124ms',
    },
  };

  const healthData = data || mockHealthData;
  const isHealthy = healthData.status === 'healthy';

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'green';
      case 'warning': return 'yellow';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const getUsageColor = (usage) => {
    if (usage < 50) return 'green';
    if (usage < 80) return 'yellow';
    return 'red';
  };

  return (
    <MotionBox
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardHeader>
          <HStack justify="space-between">
            <HStack>
              <Box p={2} borderRadius="lg" bg="green.100" color="green.600">
                <Activity size={20} />
              </Box>
              <Heading size="md">System Health</Heading>
            </HStack>
            <Badge
              colorScheme={getHealthColor(healthData.status)}
              variant="solid"
              textTransform="capitalize"
            >
              {healthData.status}
            </Badge>
          </HStack>
        </CardHeader>
        <CardBody pt={0}>
          <VStack spacing={6} align="stretch">
            {/* System Metrics */}
            <Grid templateColumns="1fr 1fr" gap={4}>
              <Box>
                <Text fontSize="sm" color="gray.500" mb={2}>
                  CPU Usage
                </Text>
                <Progress
                  value={healthData.details.system.cpu_usage}
                  colorScheme={getUsageColor(healthData.details.system.cpu_usage)}
                  size="lg"
                  borderRadius="md"
                />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {healthData.details.system.cpu_usage.toFixed(1)}%
                </Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="gray.500" mb={2}>
                  Memory Usage
                </Text>
                <Progress
                  value={healthData.details.system.memory_usage}
                  colorScheme={getUsageColor(healthData.details.system.memory_usage)}
                  size="lg"
                  borderRadius="md"
                />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {healthData.details.system.memory_usage.toFixed(1)}%
                </Text>
              </Box>
            </Grid>

            {/* Components Status */}
            <Box>
              <Text fontSize="sm" color="gray.500" mb={3}>
                Components
              </Text>
              <VStack spacing={2}>
                {Object.entries(healthData.details.components).map(([component, status]) => (
                  <HStack key={component} justify="space-between" w="full">
                    <HStack>
                      {component === 'redis' && <Database size={16} color="gray.500" />}
                      {component === 'database' && <Server size={16} color="gray.500" />}
                      {component === 'api' && <Zap size={16} color="gray.500" />}
                      <Text fontSize="sm" textTransform="capitalize">
                        {component}
                      </Text>
                    </HStack>
                    <Badge
                      size="sm"
                      colorScheme={getHealthColor(status)}
                      variant="subtle"
                    >
                      {status}
                    </Badge>
                  </HStack>
                ))}
              </VStack>
            </Box>

            {/* Performance Stats */}
            <Grid templateColumns="1fr 1fr" gap={4}>
              <Stat size="sm">
                <StatLabel fontSize="xs">Uptime</StatLabel>
                <StatNumber fontSize="md">{healthData.details.uptime}</StatNumber>
              </Stat>
              <Stat size="sm">
                <StatLabel fontSize="xs">Response Time</StatLabel>
                <StatNumber fontSize="md">{healthData.details.response_time}</StatNumber>
              </Stat>
            </Grid>

            {!isHealthy && (
              <Alert status="warning" size="sm" borderRadius="md">
                <AlertIcon />
                <Text fontSize="sm">Some components need attention</Text>
              </Alert>
            )}
          </VStack>
        </CardBody>
      </Card>
    </MotionBox>
  );
};

export default SystemHealthCard;
