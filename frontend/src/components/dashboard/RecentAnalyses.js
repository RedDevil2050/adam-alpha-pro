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
  Button,
  useColorModeValue,
  Avatar,
  Flex,
} from '@chakra-ui/react';
import { Clock, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

const MotionBox = motion(Box);

const RecentAnalyses = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const navigate = useNavigate();

  // Mock recent analyses data
  const recentAnalyses = [
    {
      id: 1,
      symbol: 'AAPL',
      verdict: 'BUY',
      confidence: 0.85,
      timestamp: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
      change: '+2.34%',
      trend: 'up',
    },
    {
      id: 2,
      symbol: 'TSLA',
      verdict: 'HOLD',
      confidence: 0.67,
      timestamp: new Date(Date.now() - 45 * 60 * 1000), // 45 minutes ago
      change: '-1.12%',
      trend: 'down',
    },
    {
      id: 3,
      symbol: 'MSFT',
      verdict: 'BUY',
      confidence: 0.92,
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
      change: '+0.87%',
      trend: 'up',
    },
    {
      id: 4,
      symbol: 'GOOGL',
      verdict: 'SELL',
      confidence: 0.78,
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
      change: '-3.21%',
      trend: 'down',
    },
  ];
  const getVerdictColor = (verdict) => {
    if (!verdict) return 'gray';
    switch (verdict) {
      case 'BUY': return 'green';
      case 'SELL': return 'red';
      case 'HOLD': return 'yellow';
      default: return 'gray';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'yellow';
    return 'red';
  };

  return (
    <MotionBox
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px">
        <CardHeader>
          <HStack justify="space-between">
            <HStack>
              <Box p={2} borderRadius="lg" bg="purple.100" color="purple.600">
                <Clock size={20} />
              </Box>
              <Heading size="md">Recent Analyses</Heading>
            </HStack>
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/analysis')}
            >
              View All
            </Button>
          </HStack>
        </CardHeader>
        <CardBody pt={0}>
          <VStack spacing={4} align="stretch">
            {recentAnalyses.map((analysis, index) => (
              <MotionBox
                key={analysis.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <Box
                  p={4}
                  borderRadius="lg"
                  bg={useColorModeValue('gray.50', 'gray.700')}
                  border="1px"
                  borderColor={useColorModeValue('gray.200', 'gray.600')}
                  _hover={{
                    borderColor: 'brand.300',
                    cursor: 'pointer',
                    transform: 'translateY(-1px)',
                  }}
                  transition="all 0.2s"
                  onClick={() => navigate(`/analysis/${analysis.symbol}`)}
                >
                  <Flex justify="space-between" align="center">
                    <HStack spacing={3}>
                      <Avatar
                        size="sm"
                        name={analysis.symbol}
                        bg="brand.500"
                        color="white"
                        fontSize="xs"
                      />
                      <VStack align="start" spacing={0}>
                        <HStack>
                          <Text fontWeight="bold" fontSize="sm">
                            {analysis.symbol}
                          </Text>
                          <Badge
                            colorScheme={getVerdictColor(analysis.verdict)}
                            variant="solid"
                            fontSize="xs"
                          >
                            {analysis.verdict}
                          </Badge>
                        </HStack>
                        <HStack spacing={2}>
                          <Text fontSize="xs" color="gray.500">
                            Confidence: {(analysis.confidence * 100).toFixed(0)}%
                          </Text>
                          <Badge
                            size="sm"
                            colorScheme={getConfidenceColor(analysis.confidence)}
                            variant="subtle"
                          >
                            {analysis.confidence >= 0.8 ? 'High' : 
                             analysis.confidence >= 0.6 ? 'Medium' : 'Low'}
                          </Badge>
                        </HStack>
                      </VStack>
                    </HStack>

                    <VStack align="end" spacing={1}>
                      <HStack spacing={1}>
                        {analysis.trend === 'up' ? (
                          <TrendingUp size={14} color="green" />
                        ) : (
                          <TrendingDown size={14} color="red" />
                        )}
                        <Text
                          fontSize="sm"
                          fontWeight="medium"
                          color={analysis.trend === 'up' ? 'green.500' : 'red.500'}
                        >
                          {analysis.change}
                        </Text>
                      </HStack>
                      <Text fontSize="xs" color="gray.500">
                        {formatDistanceToNow(analysis.timestamp, { addSuffix: true })}
                      </Text>
                    </VStack>
                  </Flex>
                </Box>
              </MotionBox>
            ))}

            <Button
              variant="ghost"
              size="sm"
              leftIcon={<BarChart3 size={16} />}
              onClick={() => navigate('/analysis')}
              w="full"
            >
              Start New Analysis
            </Button>
          </VStack>
        </CardBody>
      </Card>
    </MotionBox>
  );
};

export default RecentAnalyses;
