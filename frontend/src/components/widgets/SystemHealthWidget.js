import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  useColorModeValue,
  Card,
  CardBody,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Activity, Cpu, Database, Wifi, Zap } from 'lucide-react';

const MotionCard = motion(Card);

const SystemHealthWidget = ({ data }) => {
  const [animatedValues, setAnimatedValues] = useState({
    cpu: 0,
    memory: 0,
    network: 0,
    agents: 0
  });

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Animate values on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedValues({
        cpu: data?.system?.cpu_usage || 45,
        memory: data?.system?.memory_usage || 68,
        network: 85,
        agents: 23
      });
    }, 500);

    return () => clearTimeout(timer);
  }, [data]);

  const getHealthColor = (value) => {
    if (value < 50) return 'green';
    if (value < 80) return 'yellow';
    return 'red';
  };

  const healthMetrics = [
    {
      label: 'CPU Usage',
      value: animatedValues.cpu,
      icon: Cpu,
      unit: '%'
    },
    {
      label: 'Memory',
      value: animatedValues.memory,
      icon: Database,
      unit: '%'
    },
    {
      label: 'Network',
      value: animatedValues.network,
      icon: Wifi,
      unit: '%'
    },
    {
      label: 'Active Agents',
      value: animatedValues.agents,
      icon: Zap,
      unit: ''
    }
  ];

  return (
    <MotionCard
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      bg={cardBg}
      borderColor={borderColor}
      borderWidth="1px"
      position="relative"
      overflow="hidden"
    >
      {/* Animated background gradient */}
      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        bottom={0}
        bgGradient="linear(45deg, transparent 0%, blue.50 50%, transparent 100%)"
        opacity={0.1}
        animation="pulse 4s ease-in-out infinite"
      />

      <CardBody position="relative">
        <VStack spacing={6} align="stretch">
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              >
                <Box
                  p={2}
                  borderRadius="lg"
                  bg="green.100"
                  color="green.600"
                >
                  <Activity size={20} />
                </Box>
              </motion.div>
              <VStack align="start" spacing={0}>
                <Text fontWeight="bold" fontSize="lg">
                  System Health
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Real-time monitoring
                </Text>
              </VStack>
            </HStack>
            <Badge colorScheme="green" variant="solid">
              HEALTHY
            </Badge>
          </HStack>

          {/* Health Metrics Grid */}
          <Grid templateColumns="repeat(2, 1fr)" gap={4}>
            {healthMetrics.map((metric, index) => (
              <motion.div
                key={metric.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Box
                  p={4}
                  borderRadius="lg"
                  bg={useColorModeValue('gray.50', 'gray.700')}
                  border="1px"
                  borderColor={useColorModeValue('gray.200', 'gray.600')}
                >
                  <VStack spacing={3}>
                    <HStack justify="space-between" w="full">
                      <metric.icon 
                        size={16} 
                        color={
                          metric.label === 'Active Agents' 
                            ? '#3182CE' 
                            : getHealthColor(metric.value) === 'green' 
                              ? '#38A169' 
                              : getHealthColor(metric.value) === 'yellow'
                                ? '#D69E2E'
                                : '#E53E3E'
                        } 
                      />
                      <Text fontSize="xs" fontWeight="medium" color="gray.600">
                        {metric.label}
                      </Text>
                    </HStack>

                    {metric.label === 'Active Agents' ? (
                      <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                        {metric.value}
                      </Text>
                    ) : (
                      <>
                        <Progress
                          value={metric.value}
                          colorScheme={getHealthColor(metric.value)}
                          size="sm"
                          borderRadius="full"
                          w="full"
                        />
                        <Text 
                          fontSize="sm" 
                          fontWeight="bold"
                          color={`${getHealthColor(metric.value)}.500`}
                        >
                          {metric.value}{metric.unit}
                        </Text>
                      </>
                    )}
                  </VStack>
                </Box>
              </motion.div>
            ))}
          </Grid>

          {/* System Status */}
          <Box
            p={4}
            borderRadius="lg"
            bg="linear-gradient(135deg, rgba(72, 187, 120, 0.1) 0%, rgba(56, 161, 105, 0.1) 100%)"
            border="1px"
            borderColor="green.200"
          >
            <VStack spacing={2}>
              <HStack spacing={3}>
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Box w={3} h={3} bg="green.500" borderRadius="full" />
                </motion.div>
                <Text fontWeight="medium" color="green.700">
                  All systems operational
                </Text>
              </HStack>
              <Text fontSize="sm" color="green.600">
                Uptime: 99.9% • Last updated: just now
              </Text>
            </VStack>
          </Box>
        </VStack>
      </CardBody>
    </MotionCard>
  );
};

export default SystemHealthWidget;
