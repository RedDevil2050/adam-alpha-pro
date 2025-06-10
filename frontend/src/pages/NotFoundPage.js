import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  Button,
  useColorModeValue,
  Icon,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { FiHome, FiArrowLeft } from 'react-icons/fi';
import { Link as RouterLink } from 'react-router-dom';

const MotionBox = motion(Box);

const NotFoundPage = () => {
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  
  return (
    <Box bg={bgColor} minH="100vh" display="flex" alignItems="center" justifyContent="center">
      <Container maxW="md" textAlign="center">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <VStack spacing={8}>
            {/* 404 Animation */}
            <MotionBox
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Text
                fontSize={{ base: '6xl', md: '8xl' }}
                fontWeight="bold"
                bgGradient="linear(to-r, blue.400, purple.500, pink.500)"
                bgClip="text"
                lineHeight="1"
              >
                404
              </Text>
            </MotionBox>

            {/* Error Message */}
            <VStack spacing={4}>
              <Heading size="lg" color="gray.600">
                Page Not Found
              </Heading>
              <Text color="gray.500" fontSize="lg" maxW="md">
                Oops! The page you're looking for doesn't exist. It might have been moved, deleted, or you entered the wrong URL.
              </Text>
            </VStack>

            {/* Action Buttons */}
            <VStack spacing={4}>
              <Button
                as={RouterLink}
                to="/"
                leftIcon={<Icon as={FiHome} />}
                colorScheme="blue"
                size="lg"
                px={8}
              >
                Go Home
              </Button>
              <Button
                leftIcon={<Icon as={FiArrowLeft} />}
                variant="ghost"
                onClick={() => window.history.back()}
              >
                Go Back
              </Button>
            </VStack>

            {/* Decorative Elements */}
            <MotionBox
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.1 }}
              transition={{ duration: 1, delay: 0.5 }}
              position="absolute"
              top="20%"
              left="10%"
              transform="rotate(-10deg)"
              pointerEvents="none"
            >
              <Text fontSize="2xl" color="blue.500">
                📈
              </Text>
            </MotionBox>
            
            <MotionBox
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.1 }}
              transition={{ duration: 1, delay: 0.7 }}
              position="absolute"
              top="30%"
              right="15%"
              transform="rotate(15deg)"
              pointerEvents="none"
            >
              <Text fontSize="3xl" color="green.500">
                💰
              </Text>
            </MotionBox>
            
            <MotionBox
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.1 }}
              transition={{ duration: 1, delay: 0.9 }}
              position="absolute"
              bottom="20%"
              left="20%"
              transform="rotate(-20deg)"
              pointerEvents="none"
            >
              <Text fontSize="2xl" color="purple.500">
                📊
              </Text>
            </MotionBox>
          </VStack>
        </MotionBox>
      </Container>
    </Box>
  );
};

export default NotFoundPage;
