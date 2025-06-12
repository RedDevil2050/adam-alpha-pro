import React from 'react';
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
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Progress,
  useColorModeValue,
  Flex,
  Avatar,
  Divider,
} from '@chakra-ui/react';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Activity,
  Zap,
  Shield,
  Award,
} from 'lucide-react';
import { motion } from 'framer-motion';

const MotionCard = motion(Card);
const MotionBox = motion(Box);

const AnalysisResults = ({ data, symbol }) => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Mock comprehensive analysis data structure based on your backend
  const mockData = {
    symbol: symbol,
    overall_verdict: 'BUY',
    overall_confidence: 0.78,
    overall_score: 7.8,
    timestamp: new Date().toISOString(),
    categories: {
      technical: {
        verdict: 'BUY',
        confidence: 0.82,
        score: 8.2,
        agents_count: 8,
        key_insights: [
          'RSI indicates oversold condition',
          'MACD showing bullish crossover',
          'Strong momentum in last 5 days'
        ]
      },
      fundamental: {
        verdict: 'HOLD',
        confidence: 0.71,
        score: 7.1,
        agents_count: 6,
        key_insights: [
          'P/E ratio slightly above sector average',
          'Strong earnings growth last quarter',
          'Debt-to-equity ratio improving'
        ]
      },
      sentiment: {
        verdict: 'BUY',
        confidence: 0.85,
        score: 8.5,
        agents_count: 4,
        key_insights: [
          'Positive news sentiment trending',
          'Social media mentions increasing',
          'Analyst upgrades outnumber downgrades'
        ]
      },
      risk: {
        verdict: 'MODERATE',
        confidence: 0.69,
        score: 6.9,
        agents_count: 5,
        key_insights: [
          'Volatility within normal range',
          'Beta indicates market correlation',
          'VaR suggests manageable downside'
        ]
      }
    },
    price_data: {
      current_price: 185.42,
      change: 3.27,
      change_percent: 1.8,
      volume: 2450000,
      market_cap: '2.89T'
    }
  };
  const analysisData = data || mockData;

  // Safe data access with fallbacks
  const priceData = analysisData.price_data || {
    current_price: 0,
    change: 0,
    change_percent: 0,
    volume: 0,
    market_cap: 'N/A'
  };

  const categories = analysisData.categories || {};
  const overallVerdict = analysisData.overall_verdict || 'UNKNOWN';
  const overallConfidence = analysisData.overall_confidence || 0;
  const overallScore = analysisData.overall_score || 0;
  const timestamp = analysisData.timestamp || new Date().toISOString();

  const getVerdictColor = (verdict) => {
    if (!verdict || typeof verdict !== 'string') return 'gray';
    switch (verdict.toUpperCase()) {
      case 'BUY': return 'green';
      case 'STRONG_BUY': return 'green';
      case 'SELL': return 'red';
      case 'STRONG_SELL': return 'red';
      case 'HOLD': return 'yellow';
      case 'MODERATE': return 'orange';
      default: return 'gray';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'yellow';
    return 'red';
  };

  const categoryIcons = {
    technical: Activity,
    fundamental: Target,
    sentiment: Zap,
    risk: Shield,
  };

  return (
    <VStack spacing={8} align="stretch">
      {/* Overall Summary */}
      <MotionCard
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        bg={cardBg}
        borderColor={borderColor}
        borderWidth="1px"
      >
        <CardHeader>
          <HStack justify="space-between">
            <HStack spacing={4}>
              <Avatar
                size="lg"
                name={analysisData.symbol}
                bg="brand.500"
                color="white"
                fontSize="xl"
                fontWeight="bold"
              />              <VStack align="start" spacing={1}>
                <Heading size="lg">{analysisData.symbol}</Heading>
                <HStack>
                  <Badge
                    colorScheme={getVerdictColor(overallVerdict)}
                    variant="solid"
                    fontSize="sm"
                    px={3}
                    py={1}
                  >
                    {overallVerdict}
                  </Badge>
                  <Badge
                    colorScheme={getConfidenceColor(overallConfidence)}
                    variant="outline"
                  >
                    {(overallConfidence * 100).toFixed(0)}% Confidence
                  </Badge>
                </HStack>
              </VStack>
            </HStack>
            <VStack align="end" spacing={1}>
              <Text fontSize="3xl" fontWeight="bold">
                ${priceData.current_price}
              </Text>
              <HStack>
                {priceData.change > 0 ? (
                  <TrendingUp size={16} color="green" />
                ) : (
                  <TrendingDown size={16} color="red" />
                )}
                <Text
                  color={priceData.change > 0 ? 'green.500' : 'red.500'}
                  fontWeight="medium"
                >
                  {priceData.change > 0 ? '+' : ''}
                  {priceData.change} ({priceData.change_percent}%)
                </Text>
              </HStack>
            </VStack>
          </HStack>
        </CardHeader>
        <CardBody pt={0}>          <Grid templateColumns="repeat(4, 1fr)" gap={6}>
            <Stat>
              <StatLabel>Overall Score</StatLabel>
              <StatNumber>{overallScore}/10</StatNumber>
              <Progress
                value={overallScore * 10}
                colorScheme={getVerdictColor(overallVerdict)}
                size="sm"
                mt={2}
              />
            </Stat>
            <Stat>
              <StatLabel>Volume</StatLabel>
              <StatNumber fontSize="lg">
                {priceData.volume ? (priceData.volume / 1000000).toFixed(1) + 'M' : 'N/A'}
              </StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Market Cap</StatLabel>
              <StatNumber fontSize="lg">{priceData.market_cap}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Analysis Time</StatLabel>
              <StatNumber fontSize="sm">
                {new Date(timestamp).toLocaleTimeString()}
              </StatNumber>
            </Stat>
          </Grid>
        </CardBody>
      </MotionCard>      {/* Category Breakdown */}
      <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={6}>
        {Object.entries(categories).map(([category, data], index) => {
          const Icon = categoryIcons[category] || Activity;
          const verdict = data?.verdict || 'UNKNOWN';
          const confidence = data?.confidence || 0;
          const score = data?.score || 0;
          const agentsCount = data?.agents_count || 0;
          const keyInsights = data?.key_insights || [];
          
          return (
            <MotionCard
              key={category}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              bg={cardBg}
              borderColor={borderColor}
              borderWidth="1px"
            >
              <CardHeader>
                <HStack justify="space-between">
                  <HStack>
                    <Box
                      p={2}
                      borderRadius="lg"
                      bg={`${getVerdictColor(verdict)}.100`}
                      color={`${getVerdictColor(verdict)}.600`}
                    >
                      <Icon size={20} />
                    </Box>
                    <VStack align="start" spacing={0}>
                      <Heading size="md" textTransform="capitalize">
                        {category}
                      </Heading>
                      <Text fontSize="sm" color="gray.500">
                        {agentsCount} agents
                      </Text>
                    </VStack>
                  </HStack>
                  <Badge
                    colorScheme={getVerdictColor(verdict)}
                    variant="solid"
                  >
                    {verdict}
                  </Badge>
                </HStack>
              </CardHeader>
              <CardBody pt={0}>
                <VStack spacing={4} align="stretch">
                  <HStack justify="space-between">
                    <Text fontSize="sm" color="gray.500">Score</Text>
                    <Text fontWeight="bold">{score}/10</Text>
                  </HStack>
                  <Progress
                    value={score * 10}
                    colorScheme={getVerdictColor(verdict)}
                    size="md"
                    borderRadius="full"
                  />
                  <HStack justify="space-between">
                    <Text fontSize="sm" color="gray.500">Confidence</Text>
                    <Badge
                      colorScheme={getConfidenceColor(confidence)}
                      variant="subtle"
                    >
                      {(confidence * 100).toFixed(0)}%
                    </Badge>
                  </HStack>
                  
                  <Divider />
                  
                  <VStack align="start" spacing={2}>
                    <Text fontSize="sm" fontWeight="medium" color="gray.600">
                      Key Insights:
                    </Text>
                    {keyInsights.slice(0, 3).map((insight, i) => (
                      <HStack key={i} spacing={2} align="start">
                        <Box
                          w={1.5}
                          h={1.5}
                          bg="brand.500"
                          borderRadius="full"
                          mt={2}
                          flexShrink={0}
                        />
                        <Text fontSize="sm" color="gray.600">
                          {insight}
                        </Text>
                      </HStack>
                    ))}
                    {keyInsights.length === 0 && (
                      <Text fontSize="sm" color="gray.500" fontStyle="italic">
                        No insights available
                      </Text>
                    )}
                  </VStack>
                </VStack>
              </CardBody>
            </MotionCard>
          );
        })}
      </Grid>
    </VStack>
  );
};

export default AnalysisResults;
