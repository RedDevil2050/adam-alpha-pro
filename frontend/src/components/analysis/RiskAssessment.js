import React from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  SimpleGrid,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  useColorModeValue,
  Icon,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  FiTrendingUp, 
  FiTrendingDown, 
  FiAlertTriangle, 
  FiShield,
  FiBarChart3,
  FiPieChart
} from 'react-icons/fi';

const MotionCard = motion(Card);

const RiskAssessment = ({ riskData }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  if (!riskData) {
    return (
      <Card bg={bgColor} borderColor={borderColor} borderWidth="1px">
        <CardBody>
          <Text color="gray.500">No risk assessment data available</Text>
        </CardBody>
      </Card>
    );
  }

  const getRiskColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'low': return 'green';
      case 'medium': return 'yellow';
      case 'high': return 'orange';
      case 'very high': return 'red';
      default: return 'gray';
    }
  };

  const getRiskScore = (score) => {
    if (score >= 80) return { color: 'red', label: 'Very High' };
    if (score >= 60) return { color: 'orange', label: 'High' };
    if (score >= 40) return { color: 'yellow', label: 'Medium' };
    if (score >= 20) return { color: 'blue', label: 'Low' };
    return { color: 'green', label: 'Very Low' };
  };

  const formatValue = (value, decimals = 2) => {
    if (typeof value === 'number') {
      return value.toFixed(decimals);
    }
    return value;
  };

  const overallRisk = getRiskScore(riskData.overall_score || 50);

  return (
    <MotionCard
      bg={bgColor}
      borderColor={borderColor}
      borderWidth="1px"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <CardHeader>
        <HStack>
          <Icon as={FiShield} color={overallRisk.color + '.500'} />
          <Heading size="md">Risk Assessment</Heading>
        </HStack>
      </CardHeader>
      <CardBody>
        <VStack spacing={6} align="stretch">
          {/* Overall Risk Score */}
          <Box>
            <Text fontWeight="semibold" mb={3}>Overall Risk Level</Text>
            <VStack spacing={3}>
              <HStack justify="space-between" w="full">
                <Text>Risk Score</Text>
                <Badge colorScheme={overallRisk.color} size="lg" p={2}>
                  {overallRisk.label}
                </Badge>
              </HStack>
              <Progress 
                value={riskData.overall_score || 50} 
                colorScheme={overallRisk.color}
                size="lg"
                w="full"
                borderRadius="md"
              />
              <Text fontSize="sm" color="gray.500" alignSelf="flex-end">
                {formatValue(riskData.overall_score || 50)}/100
              </Text>
            </VStack>
          </Box>

          {/* Risk Factors */}
          {riskData.risk_factors && (
            <Box>
              <Text fontWeight="semibold" mb={3}>Risk Factors</Text>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                {/* Market Risk */}
                {riskData.risk_factors.market_risk && (
                  <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <HStack justify="space-between" mb={2}>
                      <HStack>
                        <Icon as={FiBarChart3} color="blue.500" />
                        <Text fontSize="sm" fontWeight="semibold">Market Risk</Text>
                      </HStack>
                      <Badge colorScheme={getRiskColor(riskData.risk_factors.market_risk.level)}>
                        {riskData.risk_factors.market_risk.level}
                      </Badge>
                    </HStack>
                    <Progress 
                      value={riskData.risk_factors.market_risk.score} 
                      colorScheme={getRiskColor(riskData.risk_factors.market_risk.level)}
                      size="sm"
                      mb={2}
                    />
                    <Text fontSize="xs" color="gray.500">
                      {riskData.risk_factors.market_risk.description}
                    </Text>
                  </Box>
                )}

                {/* Volatility Risk */}
                {riskData.risk_factors.volatility_risk && (
                  <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <HStack justify="space-between" mb={2}>
                      <HStack>
                        <Icon as={FiTrendingUp} color="orange.500" />
                        <Text fontSize="sm" fontWeight="semibold">Volatility Risk</Text>
                      </HStack>
                      <Badge colorScheme={getRiskColor(riskData.risk_factors.volatility_risk.level)}>
                        {riskData.risk_factors.volatility_risk.level}
                      </Badge>
                    </HStack>
                    <Progress 
                      value={riskData.risk_factors.volatility_risk.score} 
                      colorScheme={getRiskColor(riskData.risk_factors.volatility_risk.level)}
                      size="sm"
                      mb={2}
                    />
                    <Text fontSize="xs" color="gray.500">
                      {riskData.risk_factors.volatility_risk.description}
                    </Text>
                  </Box>
                )}

                {/* Liquidity Risk */}
                {riskData.risk_factors.liquidity_risk && (
                  <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <HStack justify="space-between" mb={2}>
                      <HStack>
                        <Icon as={FiPieChart} color="purple.500" />
                        <Text fontSize="sm" fontWeight="semibold">Liquidity Risk</Text>
                      </HStack>
                      <Badge colorScheme={getRiskColor(riskData.risk_factors.liquidity_risk.level)}>
                        {riskData.risk_factors.liquidity_risk.level}
                      </Badge>
                    </HStack>
                    <Progress 
                      value={riskData.risk_factors.liquidity_risk.score} 
                      colorScheme={getRiskColor(riskData.risk_factors.liquidity_risk.level)}
                      size="sm"
                      mb={2}
                    />
                    <Text fontSize="xs" color="gray.500">
                      {riskData.risk_factors.liquidity_risk.description}
                    </Text>
                  </Box>
                )}

                {/* Credit Risk */}
                {riskData.risk_factors.credit_risk && (
                  <Box p={4} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <HStack justify="space-between" mb={2}>
                      <HStack>
                        <Icon as={FiTrendingDown} color="red.500" />
                        <Text fontSize="sm" fontWeight="semibold">Credit Risk</Text>
                      </HStack>
                      <Badge colorScheme={getRiskColor(riskData.risk_factors.credit_risk.level)}>
                        {riskData.risk_factors.credit_risk.level}
                      </Badge>
                    </HStack>
                    <Progress 
                      value={riskData.risk_factors.credit_risk.score} 
                      colorScheme={getRiskColor(riskData.risk_factors.credit_risk.level)}
                      size="sm"
                      mb={2}
                    />
                    <Text fontSize="xs" color="gray.500">
                      {riskData.risk_factors.credit_risk.description}
                    </Text>
                  </Box>
                )}
              </SimpleGrid>
            </Box>
          )}

          {/* Risk Metrics */}
          {riskData.metrics && (
            <Box>
              <Text fontWeight="semibold" mb={3}>Risk Metrics</Text>
              <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                {riskData.metrics.beta && (
                  <Box textAlign="center" p={3} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <Text fontSize="lg" fontWeight="bold">
                      {formatValue(riskData.metrics.beta)}
                    </Text>
                    <Text fontSize="sm" color="gray.500">Beta</Text>
                  </Box>
                )}
                {riskData.metrics.sharpe_ratio && (
                  <Box textAlign="center" p={3} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <Text fontSize="lg" fontWeight="bold">
                      {formatValue(riskData.metrics.sharpe_ratio)}
                    </Text>
                    <Text fontSize="sm" color="gray.500">Sharpe Ratio</Text>
                  </Box>
                )}
                {riskData.metrics.var && (
                  <Box textAlign="center" p={3} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <Text fontSize="lg" fontWeight="bold" color="red.500">
                      {formatValue(riskData.metrics.var)}%
                    </Text>
                    <Text fontSize="sm" color="gray.500">VaR (95%)</Text>
                  </Box>
                )}
                {riskData.metrics.max_drawdown && (
                  <Box textAlign="center" p={3} borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
                    <Text fontSize="lg" fontWeight="bold" color="red.500">
                      {formatValue(riskData.metrics.max_drawdown)}%
                    </Text>
                    <Text fontSize="sm" color="gray.500">Max Drawdown</Text>
                  </Box>
                )}
              </SimpleGrid>
            </Box>
          )}

          {/* Risk Warnings */}
          {riskData.warnings && riskData.warnings.length > 0 && (
            <Box>
              <Text fontWeight="semibold" mb={3}>Risk Warnings</Text>
              <VStack spacing={3} align="stretch">
                {riskData.warnings.map((warning, index) => (
                  <Alert key={index} status={warning.severity || 'warning'} borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>{warning.title}</AlertTitle>
                      <AlertDescription>{warning.message}</AlertDescription>
                    </Box>
                  </Alert>
                ))}
              </VStack>
            </Box>
          )}

          {/* Recommendations */}
          {riskData.recommendations && riskData.recommendations.length > 0 && (
            <Box>
              <Text fontWeight="semibold" mb={3}>Risk Management Recommendations</Text>
              <VStack spacing={2} align="stretch">
                {riskData.recommendations.map((rec, index) => (
                  <Box key={index} p={3} borderRadius="md" bg={useColorModeValue('blue.50', 'blue.900')} borderLeft="4px" borderColor="blue.500">
                    <Text fontSize="sm">{rec}</Text>
                  </Box>
                ))}
              </VStack>
            </Box>
          )}

          {/* Risk Summary */}
          {riskData.summary && (
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              <Box>
                <AlertTitle>Risk Summary</AlertTitle>
                <AlertDescription>{riskData.summary}</AlertDescription>
              </Box>
            </Alert>
          )}
        </VStack>
      </CardBody>
    </MotionCard>
  );
};

export default RiskAssessment;
