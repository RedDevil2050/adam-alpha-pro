import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Progress,
  useColorModeValue,
  Fade,
  ScaleFade,
  SlideFade,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Zap, TrendingUp, Activity, CheckCircle, AlertTriangle } from 'lucide-react';

const MotionBox = motion(Box);

const RealTimeAnalysisStream = ({ symbol, analysisData }) => {
  const [currentAgent, setCurrentAgent] = useState(null);
  const [completedAgents, setCompletedAgents] = useState([]);
  const [progress, setProgress] = useState(0);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Simulate real-time agent execution
  useEffect(() => {
    if (!analysisData) return;

    const agents = [
      { name: 'Technical Analysis Agent', icon: TrendingUp, duration: 2000 },
      { name: 'Fundamental Analysis Agent', icon: Activity, duration: 3000 },
      { name: 'Sentiment Analysis Agent', icon: Zap, duration: 2500 },
      { name: 'Risk Assessment Agent', icon: AlertTriangle, duration: 1500 },
      { name: 'ESG Scoring Agent', icon: CheckCircle, duration: 2000 },
    ];

    let currentIndex = 0;
    const executeAgent = () => {
      if (currentIndex < agents.length) {
        const agent = agents[currentIndex];
        setCurrentAgent(agent);
        setProgress(((currentIndex + 1) / agents.length) * 100);

        setTimeout(() => {
          setCompletedAgents(prev => [...prev, agent]);
          currentIndex++;
          executeAgent();
        }, agent.duration);
      } else {
        setCurrentAgent(null);
      }
    };

    executeAgent();
  }, [analysisData]);

  if (!analysisData && !currentAgent) return null;

  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box
        bg={cardBg}
        borderRadius="xl"
        p={6}
        border="1px"
        borderColor={borderColor}
        boxShadow="lg"
      >
        <VStack spacing={4} align="stretch">
          {/* Header */}
          <HStack justify="space-between">
            <HStack>
              <Box
                p={2}
                borderRadius="lg"
                bg="blue.100"
                color="blue.600"
              >
                <Activity size={20} />
              </Box>
              <VStack align="start" spacing={0}>
                <Text fontWeight="bold" fontSize="lg">
                  Live Analysis: {symbol}
                </Text>
                <Text fontSize="sm" color="gray.500">
                  AI agents processing in real-time
                </Text>
              </VStack>
            </HStack>
            <Badge colorScheme="green" variant="solid">
              <HStack spacing={1}>
                <Box w={2} h={2} bg="white" borderRadius="full" />
                <Text>LIVE</Text>
              </HStack>
            </Badge>
          </HStack>

          {/* Progress Bar */}
          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" color="gray.600">
                Analysis Progress
              </Text>
              <Text fontSize="sm" fontWeight="medium">
                {Math.round(progress)}%
              </Text>
            </HStack>
            <Progress
              value={progress}
              colorScheme="blue"
              size="lg"
              borderRadius="full"
              bg={useColorModeValue('gray.100', 'gray.700')}
            />
          </Box>

          {/* Current Agent */}
          {currentAgent && (
            <Fade in={true}>
              <Box
                p={4}
                borderRadius="lg"
                bg={useColorModeValue('blue.50', 'blue.900')}
                border="1px"
                borderColor="blue.200"
              >
                <HStack>
                  <MotionBox
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <currentAgent.icon size={20} color="#3182CE" />
                  </MotionBox>
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="medium" color="blue.700">
                      {currentAgent.name}
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      Processing data...
                    </Text>
                  </VStack>
                </HStack>
              </Box>
            </Fade>
          )}

          {/* Completed Agents */}
          {completedAgents.length > 0 && (
            <VStack spacing={2} align="stretch">
              <Text fontSize="sm" color="gray.600" fontWeight="medium">
                Completed Analysis
              </Text>
              {completedAgents.map((agent, index) => (
                <SlideFade key={agent.name} in={true} offsetY={20}>
                  <HStack
                    p={3}
                    borderRadius="md"
                    bg={useColorModeValue('green.50', 'green.900')}
                    opacity={0.8}
                  >
                    <CheckCircle size={16} color="#38A169" />
                    <Text fontSize="sm" color="green.700">
                      {agent.name}
                    </Text>
                    <Text fontSize="xs" color="green.600" ml="auto">
                      ✓ Complete
                    </Text>
                  </HStack>
                </SlideFade>
              ))}
            </VStack>
          )}

          {/* Analysis Complete */}
          {progress === 100 && (
            <ScaleFade in={true}>
              <Box
                p={4}
                borderRadius="lg"
                bg={useColorModeValue('green.50', 'green.900')}
                border="1px"
                borderColor="green.200"
                textAlign="center"
              >
                <VStack spacing={2}>
                  <CheckCircle size={24} color="#38A169" />
                  <Text fontWeight="bold" color="green.700">
                    Analysis Complete!
                  </Text>
                  <Text fontSize="sm" color="green.600">
                    All agents have finished processing {symbol}
                  </Text>
                </VStack>
              </Box>
            </ScaleFade>
          )}
        </VStack>
      </Box>
    </MotionBox>
  );
};

export default RealTimeAnalysisStream;
