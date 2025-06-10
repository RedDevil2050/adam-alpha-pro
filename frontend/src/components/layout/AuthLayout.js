import React from 'react';
import {
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  useColorModeValue,
  Container,
  Image,
} from '@chakra-ui/react';
import { TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

const AuthLayout = ({ children }) => {
  const bg = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.600', 'gray.300');

  return (
    <Box bg={bg} minH="100vh">
      <Container maxW="container.xl" py={8}>
        <Flex
          direction={{ base: 'column', lg: 'row' }}
          align="center"
          justify="center"
          minH="90vh"
          gap={12}
        >
          {/* Left Side - Branding */}
          <MotionBox
            flex={1}
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            <VStack spacing={8} align={{ base: 'center', lg: 'start' }} textAlign={{ base: 'center', lg: 'left' }}>
              <HStack>
                <Box
                  bg="brand.500"
                  p={4}
                  borderRadius="xl"
                  color="white"
                >
                  <TrendingUp size={32} />
                </Box>
                <VStack align="start" spacing={0}>
                  <Text fontSize="3xl" fontWeight="bold">
                    Zion
                  </Text>
                  <Text fontSize="lg" color={textColor}>
                    Market Analysis Platform
                  </Text>
                </VStack>
              </HStack>

              <VStack spacing={6} align={{ base: 'center', lg: 'start' }}>
                <Text fontSize="4xl" fontWeight="bold" lineHeight="shorter">
                  Advanced Market Intelligence
                  <Text as="span" color="brand.500"> at Your Fingertips</Text>
                </Text>
                
                <Text fontSize="xl" color={textColor} maxW="lg">
                  Leverage sophisticated AI agents and real-time analytics to make informed investment decisions.
                </Text>

                <VStack spacing={4} align="start">
                  <HStack>
                    <Box w={2} h={2} bg="brand.500" borderRadius="full" />
                    <Text color={textColor}>Real-time market analysis with 20+ agents</Text>
                  </HStack>
                  <HStack>
                    <Box w={2} h={2} bg="brand.500" borderRadius="full" />
                    <Text color={textColor}>Advanced portfolio optimization</Text>
                  </HStack>
                  <HStack>
                    <Box w={2} h={2} bg="brand.500" borderRadius="full" />
                    <Text color={textColor}>Comprehensive risk assessment</Text>
                  </HStack>
                  <HStack>
                    <Box w={2} h={2} bg="brand.500" borderRadius="full" />
                    <Text color={textColor}>Professional-grade insights</Text>
                  </HStack>
                </VStack>
              </VStack>
            </VStack>
          </MotionBox>

          {/* Right Side - Auth Form */}
          <MotionBox
            flex={1}
            maxW={{ base: 'md', lg: 'lg' }}
            w="full"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Box
              bg={cardBg}
              borderRadius="2xl"
              boxShadow="2xl"
              p={8}
              borderWidth="1px"
              borderColor={useColorModeValue('gray.200', 'gray.700')}
            >
              {children}
            </Box>
          </MotionBox>
        </Flex>
      </Container>
    </Box>
  );
};

export default AuthLayout;
