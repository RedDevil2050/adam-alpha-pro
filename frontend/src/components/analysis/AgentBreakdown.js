import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  Progress,
  Button,
  Collapse,
  useColorModeValue,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Flex,
  Stat,
  StatLabel,
  StatNumber,
  Code,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
} from '@chakra-ui/react';
import { 
  Activity, 
  Target, 
  Zap, 
  Shield, 
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { motion } from 'framer-motion';

const MotionCard = motion(Card);

const AgentBreakdown = ({ data, symbol }) => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Mock detailed agent data based on your backend structure
  const mockAgentData = {
    technical_agents: [
      {
        name: 'RSI Agent',
        verdict: 'BUY',
        confidence: 0.85,
        value: 28.5,
        details: { rsi: 28.5, signal: 'Oversold condition detected' },
        execution_time: '1.2s',
        status: 'success'
      },
      {
        name: 'MACD Agent',
        verdict: 'BUY',
        confidence: 0.78,
        value: 'Bullish Crossover',
        details: { macd: 2.34, signal: 1.89, histogram: 0.45 },
        execution_time: '0.8s',
        status: 'success'
      },
      {
        name: 'Momentum Agent',
        verdict: 'POSITIVE',
        confidence: 0.72,
        value: 5.2,
        details: { momentum_score: 5.2, trend: 'Strong upward momentum' },
        execution_time: '1.5s',
        status: 'success'
      },
      {
        name: 'Volume Spike Agent',
        verdict: 'ACTIVE',
        confidence: 0.69,
        value: 2.1,
        details: { volume_ratio: 2.1, spike_detected: true },
        execution_time: '0.9s',
        status: 'success'
      }
    ],
    fundamental_agents: [
      {
        name: 'P/E Ratio Agent',
        verdict: 'FAIR_VALUE',
        confidence: 0.76,
        value: 18.5,
        details: { pe_ratio: 18.5, sector_avg: 20.2, verdict: 'Below sector average' },
        execution_time: '2.1s',
        status: 'success'
      },
      {
        name: 'Earnings Yield Agent',
        verdict: 'ATTRACTIVE',
        confidence: 0.82,
        value: 0.054,
        details: { earnings_yield: 0.054, risk_free_rate: 0.045 },
        execution_time: '1.8s',
        status: 'success'
      },
      {
        name: 'Beta Agent',
        verdict: 'MODERATE_RISK',
        confidence: 0.71,
        value: 1.15,
        details: { beta: 1.15, risk_level: 'Moderate' },
        execution_time: '1.3s',
        status: 'success'
      }
    ],
    sentiment_agents: [
      {
        name: 'News Sentiment Agent',
        verdict: 'POSITIVE',
        confidence: 0.89,
        value: 0.72,
        details: { sentiment_score: 0.72, articles_analyzed: 15 },
        execution_time: '3.2s',
        status: 'success'
      },
      {
        name: 'ESG Score Agent',
        verdict: 'STRONG',
        confidence: 0.77,
        value: 8.1,
        details: { esg_score: 8.1, environmental: 8.5, social: 7.8, governance: 8.0 },
        execution_time: '2.5s',
        status: 'success'
      }
    ],
    risk_agents: [
      {
        name: 'Risk Core Agent',
        verdict: 'MODERATE_RISK',
        confidence: 0.74,
        value: 6.2,
        details: { risk_score: 6.2, volatility: 0.23, max_drawdown: 0.15 },
        execution_time: '1.7s',
        status: 'success'
      },
      {
        name: 'Volatility Agent',
        verdict: 'NORMAL',
        confidence: 0.68,
        value: 0.23,
        details: { annualized_volatility: 0.23, percentile: 45 },
        execution_time: '1.1s',
        status: 'success'
      }
    ]
  };

  const agentData = data?.agents || mockAgentData;
  const getVerdictColor = (verdict) => {
    if (!verdict || typeof verdict !== 'string') return 'gray';
    const upper = verdict.toUpperCase();
    if (upper.includes('BUY') || upper.includes('POSITIVE') || upper.includes('STRONG')) return 'green';
    if (upper.includes('SELL') || upper.includes('NEGATIVE') || upper.includes('WEAK')) return 'red';
    if (upper.includes('HOLD') || upper.includes('MODERATE') || upper.includes('FAIR')) return 'yellow';
    return 'blue';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success': return <CheckCircle size={16} color="green" />;
      case 'error': return <XCircle size={16} color="red" />;
      case 'warning': return <AlertTriangle size={16} color="orange" />;
      default: return <Clock size={16} color="gray" />;
    }
  };

  const categoryIcons = {
    technical_agents: Activity,
    fundamental_agents: Target,
    sentiment_agents: Zap,
    risk_agents: Shield,
  };

  const categoryNames = {
    technical_agents: 'Technical Analysis',
    fundamental_agents: 'Fundamental Analysis', 
    sentiment_agents: 'Sentiment Analysis',
    risk_agents: 'Risk Assessment',
  };

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary Stats */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        bg={cardBg}
        borderColor={borderColor}
        borderWidth="1px"
      >
        <CardHeader>
          <Heading size="md">Agent Execution Summary</Heading>
        </CardHeader>
        <CardBody pt={0}>
          <Grid templateColumns="repeat(4, 1fr)" gap={6}>
            <Stat>
              <StatLabel>Total Agents</StatLabel>
              <StatNumber>
                {Object.values(agentData).reduce((sum, category) => sum + category.length, 0)}
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Success Rate</StatLabel>
              <StatNumber color="green.500">100%</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Avg Execution</StatLabel>
              <StatNumber>1.6s</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Cache Hits</StatLabel>
              <StatNumber color="blue.500">15%</StatNumber>
            </Stat>
          </Grid>
        </CardBody>
      </MotionCard>

      {/* Agent Categories */}
      <Accordion allowMultiple defaultIndex={[0, 1, 2, 3]}>
        {Object.entries(agentData).map(([category, agents], categoryIndex) => {
          const Icon = categoryIcons[category];
          const categoryName = categoryNames[category];
          
          return (
            <AccordionItem key={category} border="none">
              <AccordionButton p={0} _hover={{ bg: 'transparent' }}>
                <MotionCard
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: categoryIndex * 0.1 }}
                  bg={cardBg}
                  borderColor={borderColor}
                  borderWidth="1px"
                  w="full"
                  cursor="pointer"
                  _hover={{ borderColor: 'brand.300' }}
                >
                  <CardHeader>
                    <Flex justify="space-between" align="center" w="full">
                      <HStack>
                        <Box
                          p={2}
                          borderRadius="lg"
                          bg="brand.100"
                          color="brand.600"
                        >
                          <Icon size={20} />
                        </Box>
                        <VStack align="start" spacing={0}>
                          <Heading size="md">{categoryName}</Heading>
                          <Text fontSize="sm" color="gray.500">
                            {agents.length} agents executed
                          </Text>
                        </VStack>
                      </HStack>
                      <HStack spacing={4}>
                        <Badge colorScheme="green" variant="subtle">
                          {agents.filter(a => a.status === 'success').length}/{agents.length} Success
                        </Badge>
                        <AccordionIcon />
                      </HStack>
                    </Flex>
                  </CardHeader>
                </MotionCard>
              </AccordionButton>
              
              <AccordionPanel px={0} pb={6}>
                <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap={4} mt={4}>
                  {agents.map((agent, agentIndex) => (
                    <Card
                      key={agent.name}
                      bg={useColorModeValue('gray.50', 'gray.700')}
                      borderWidth="1px"
                      borderColor={useColorModeValue('gray.200', 'gray.600')}
                      size="sm"
                    >
                      <CardHeader pb={2}>
                        <HStack justify="space-between">
                          <HStack spacing={2}>
                            {getStatusIcon(agent.status)}
                            <Text fontWeight="medium" fontSize="sm">
                              {agent.name}
                            </Text>
                          </HStack>
                          <HStack spacing={2}>
                            <Badge
                              colorScheme={getVerdictColor(agent.verdict)}
                              variant="solid"
                              fontSize="xs"
                            >
                              {agent.verdict}
                            </Badge>
                            <Text fontSize="xs" color="gray.500">
                              {agent.execution_time}
                            </Text>
                          </HStack>
                        </HStack>
                      </CardHeader>
                      <CardBody pt={0}>
                        <VStack spacing={3} align="stretch">
                          <HStack justify="space-between">
                            <Text fontSize="xs" color="gray.500">Confidence</Text>
                            <Text fontSize="sm" fontWeight="medium">
                              {(agent.confidence * 100).toFixed(0)}%
                            </Text>
                          </HStack>
                          <Progress
                            value={agent.confidence * 100}
                            colorScheme={getVerdictColor(agent.verdict)}
                            size="sm"
                            borderRadius="full"
                          />
                          
                          {typeof agent.value !== 'object' && (
                            <HStack justify="space-between">
                              <Text fontSize="xs" color="gray.500">Value</Text>
                              <Code fontSize="xs">{agent.value}</Code>
                            </HStack>
                          )}

                          <Box>
                            <Text fontSize="xs" color="gray.500" mb={2}>Details:</Text>
                            <TableContainer>
                              <Table size="sm" variant="simple">
                                <Tbody>
                                  {Object.entries(agent.details).map(([key, value]) => (
                                    <Tr key={key}>
                                      <Td fontSize="xs" py={1} px={2} textTransform="capitalize">
                                        {key.replace(/_/g, ' ')}
                                      </Td>
                                      <Td fontSize="xs" py={1} px={2} isNumeric>
                                        {typeof value === 'number' ? value.toFixed(3) : value}
                                      </Td>
                                    </Tr>
                                  ))}
                                </Tbody>
                              </Table>
                            </TableContainer>
                          </Box>
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </Grid>
              </AccordionPanel>
            </AccordionItem>
          );
        })}
      </Accordion>
    </VStack>
  );
};

export default AgentBreakdown;
