import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Grid,
  GridItem,
  useColorModeValue,
  Icon,
  Flex,
  Badge,
  Image,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Zap, 
  Shield, 
  Brain, 
  BarChart3, 
  Target,
  Activity,
  Award,
  Globe,
  Users
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AnimatedBackground from '../components/common/AnimatedBackground';

const MotionBox = motion(Box);
const MotionButton = motion(Button);

const LandingPage = () => {
  const navigate = useNavigate();
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Analysis',
      description: 'Advanced machine learning algorithms analyze market trends and predict outcomes with high accuracy.',
      color: 'purple'
    },
    {
      icon: Zap,
      title: 'Real-Time Data',
      description: 'Live market data feeds ensure you always have the latest information for informed decisions.',
      color: 'yellow'
    },
    {
      icon: Shield,
      title: 'Risk Assessment',
      description: 'Comprehensive risk analysis tools help you understand and manage portfolio volatility.',
      color: 'green'
    },
    {
      icon: Target,
      title: 'Portfolio Optimization',
      description: 'Smart allocation strategies maximize returns while minimizing risk exposure.',
      color: 'blue'
    },
    {
      icon: BarChart3,
      title: 'Technical Analysis',
      description: 'Advanced charting tools with 50+ technical indicators for detailed market analysis.',
      color: 'orange'
    },
    {
      icon: Globe,
      title: 'Global Markets',
      description: 'Access to international markets including US, Indian, and European stock exchanges.',
      color: 'teal'
    }
  ];

  const stats = [
    { number: '50K+', label: 'Active Users', icon: Users },
    { number: '1M+', label: 'Analyses Daily', icon: Activity },
    { number: '99.9%', label: 'Uptime', icon: Award },
    { number: '24/7', label: 'Support', icon: Shield }
  ];

  const handleGetStarted = () => {
    navigate('/login');
  };

  const handleWatchDemo = () => {
    // In a real app, this would open a demo video or tour
    navigate('/dashboard');
  };

  return (
    <AnimatedBackground>
      <Container maxW="container.xl" py={20}>
        <VStack spacing={20} align="center">
          {/* Hero Section */}
          <MotionBox
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            textAlign="center"
            maxW="4xl"
          >
            <VStack spacing={8}>
              <Badge 
                colorScheme="brand" 
                variant="subtle" 
                fontSize="sm" 
                px={4} 
                py={2} 
                borderRadius="full"
              >
                🚀 Advanced Market Intelligence Platform
              </Badge>
              
              <Heading 
                size="3xl" 
                bgGradient="linear(to-r, blue.400, purple.500, teal.400)"
                bgClip="text"
                lineHeight="shorter"
              >
                Master the Markets with
                <Text as="span" display="block">
                  AI-Powered Analysis
                </Text>
              </Heading>
              
              <Text 
                fontSize="xl" 
                color={textColor} 
                maxW="2xl" 
                lineHeight="tall"
              >
                Harness the power of advanced algorithms, real-time data, and intelligent insights 
                to make informed investment decisions and maximize your portfolio performance.
              </Text>
              
              <HStack spacing={4} pt={4}>
                <MotionButton
                  size="lg"
                  colorScheme="brand"
                  leftIcon={<TrendingUp size={20} />}
                  onClick={handleGetStarted}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  boxShadow="lg"
                  _hover={{ boxShadow: 'xl', transform: 'translateY(-2px)' }}
                >
                  Get Started Free
                </MotionButton>
                
                <MotionButton
                  size="lg"
                  variant="outline"
                  leftIcon={<BarChart3 size={20} />}
                  onClick={handleWatchDemo}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Watch Demo
                </MotionButton>
              </HStack>
            </VStack>
          </MotionBox>

          {/* Stats Section */}
          <MotionBox
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            w="full"
          >
            <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={8}>
              {stats.map((stat, index) => (                <MotionBox
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 + 0.3 }}
                  whileHover={{ 
                    y: -4,
                    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
                  }}
                  bg={cardBg}
                  p={6}
                  borderRadius="xl"
                  borderWidth="1px"
                  borderColor={borderColor}
                  textAlign="center"
                  boxShadow="lg"
                  cursor="pointer"
                >
                  <VStack spacing={3}>
                    <Box
                      p={3}
                      borderRadius="full"
                      bg="brand.100"
                      color="brand.600"
                    >
                      <stat.icon size={24} />
                    </Box>
                    <Heading size="xl" color="brand.500">
                      {stat.number}
                    </Heading>
                    <Text color={textColor} fontWeight="medium">
                      {stat.label}
                    </Text>
                  </VStack>
                </MotionBox>
              ))}
            </Grid>
          </MotionBox>

          {/* Features Section */}
          <MotionBox
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            w="full"
          >
            <VStack spacing={12}>
              <VStack spacing={4} textAlign="center">
                <Heading size="2xl">
                  Powerful Features for
                  <Text as="span" color="brand.500"> Smart Investing</Text>
                </Heading>
                <Text fontSize="lg" color={textColor} maxW="2xl">
                  Our comprehensive suite of tools empowers you to analyze, optimize, and execute 
                  investment strategies with confidence.
                </Text>
              </VStack>

              <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }} gap={8}>
                {features.map((feature, index) => (                  <MotionBox
                    key={feature.title}
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 + 0.5 }}
                    whileHover={{ 
                      y: -4,
                      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
                    }}
                    bg={cardBg}
                    p={8}
                    borderRadius="xl"
                    borderWidth="1px"
                    borderColor={borderColor}
                    boxShadow="lg"
                    cursor="pointer"
                  >
                    <VStack spacing={6} align="start">
                      <Box
                        p={4}
                        borderRadius="xl"
                        bg={`${feature.color}.100`}
                        color={`${feature.color}.600`}
                      >
                        <feature.icon size={28} />
                      </Box>
                      <VStack spacing={3} align="start">
                        <Heading size="md">
                          {feature.title}
                        </Heading>
                        <Text color={textColor} lineHeight="tall">
                          {feature.description}
                        </Text>
                      </VStack>
                    </VStack>
                  </MotionBox>
                ))}
              </Grid>
            </VStack>
          </MotionBox>

          {/* CTA Section */}
          <MotionBox
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            w="full"
            textAlign="center"
          >
            <Box
              bg={cardBg}
              p={12}
              borderRadius="2xl"
              borderWidth="1px"
              borderColor={borderColor}
              boxShadow="2xl"
              bgGradient="linear(to-r, brand.50, purple.50, teal.50)"
            >
              <VStack spacing={8}>
                <VStack spacing={4}>
                  <Heading size="xl">
                    Ready to Transform Your Trading?
                  </Heading>
                  <Text fontSize="lg" color={textColor} maxW="2xl">
                    Join thousands of successful investors who trust our platform 
                    for their market analysis and portfolio management needs.
                  </Text>
                </VStack>
                
                <HStack spacing={4}>
                  <MotionButton
                    size="lg"
                    colorScheme="brand"
                    leftIcon={<Zap size={20} />}
                    onClick={handleGetStarted}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    boxShadow="xl"
                  >
                    Start Free Trial
                  </MotionButton>
                  
                  <MotionButton
                    size="lg"
                    variant="ghost"
                    colorScheme="brand"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Contact Sales
                  </MotionButton>
                </HStack>
              </VStack>
            </Box>
          </MotionBox>
        </VStack>
      </Container>
    </AnimatedBackground>
  );
};

export default LandingPage;
