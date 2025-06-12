import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Spinner,
  Progress,
  useColorModeValue,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Activity } from 'lucide-react';

const MotionBox = motion(Box);

const LoadingOverlay = ({ 
  isLoading, 
  message = 'Loading...', 
  progress = null,
  showProgress = false,
  type = 'spinner' // 'spinner', 'dots', 'pulse', 'analysis'
}) => {
  const bgColor = useColorModeValue('white', 'gray.900');
  const overlayBg = useColorModeValue('rgba(255,255,255,0.9)', 'rgba(26,32,44,0.9)');

  if (!isLoading) return null;

  const renderLoadingAnimation = () => {
    switch (type) {
      case 'dots':
        return (
          <HStack spacing={2}>
            {[0, 1, 2].map((index) => (
              <MotionBox
                key={index}
                w={3}
                h={3}
                bg="brand.500"
                borderRadius="full"
                animate={{
                  scale: [1, 1.2, 1],
                  opacity: [0.7, 1, 0.7],
                }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  delay: index * 0.2,
                }}
              />
            ))}
          </HStack>
        );

      case 'pulse':
        return (
          <MotionBox
            w={16}
            h={16}
            borderRadius="full"
            bg="brand.500"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.7, 1, 0.7],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
            }}
          />
        );

      case 'analysis':
        return (
          <VStack spacing={4}>
            <MotionBox
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            >
              <Box
                p={4}
                borderRadius="xl"
                bg="brand.100"
                color="brand.600"
              >
                <BarChart3 size={32} />
              </Box>
            </MotionBox>
            
            <VStack spacing={2}>
              <HStack spacing={2}>
                {['Technical', 'Fundamental', 'Sentiment'].map((agent, index) => (
                  <MotionBox
                    key={agent}
                    px={3}
                    py={1}
                    borderRadius="full"
                    bg="gray.100"
                    color="gray.600"
                    fontSize="sm"
                    animate={{
                      opacity: [0.3, 1, 0.3],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      delay: index * 0.5,
                    }}
                  >
                    {agent}
                  </MotionBox>
                ))}
              </HStack>
              <Text fontSize="sm" color="gray.500" textAlign="center">
                AI agents analyzing market data...
              </Text>
            </VStack>
          </VStack>
        );

      case 'spinner':
      default:
        return (
          <Spinner
            size="xl"
            color="brand.500"
            thickness="4px"
            speed="0.8s"
          />
        );
    }
  };

  return (
    <MotionBox
      position="fixed"
      top={0}
      left={0}
      right={0}
      bottom={0}
      bg={overlayBg}
      backdropFilter="blur(4px)"
      zIndex={9999}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Flex
        h="full"
        align="center"
        justify="center"
      >
        <MotionBox
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <Box
            bg={bgColor}
            p={8}
            borderRadius="2xl"
            boxShadow="2xl"
            borderWidth="1px"
            borderColor={useColorModeValue('gray.200', 'gray.700')}
            textAlign="center"
            minW="300px"
          >
            <VStack spacing={6}>
              {renderLoadingAnimation()}
              
              <VStack spacing={2}>
                <Text fontWeight="medium" fontSize="lg">
                  {message}
                </Text>
                
                {showProgress && progress !== null && (
                  <Box w="full">
                    <Progress
                      value={progress}
                      colorScheme="brand"
                      size="md"
                      borderRadius="full"
                      bg={useColorModeValue('gray.100', 'gray.700')}
                    />
                    <Text fontSize="sm" color="gray.500" mt={2}>
                      {Math.round(progress)}% complete
                    </Text>
                  </Box>
                )}
                
                {type === 'analysis' && (
                  <HStack spacing={1} pt={2}>
                    <Activity size={12} color="green" />
                    <Text fontSize="xs" color="green.500">
                      Real-time processing
                    </Text>
                  </HStack>
                )}
              </VStack>
            </VStack>
          </Box>
        </MotionBox>
      </Flex>
    </MotionBox>
  );
};

// Mini loading component for inline use
export const MiniLoader = ({ size = 'sm', color = 'brand.500' }) => {
  return (
    <HStack spacing={1}>
      {[0, 1, 2].map((index) => (
        <MotionBox
          key={index}
          w={size === 'sm' ? 1.5 : 2}
          h={size === 'sm' ? 1.5 : 2}
          bg={color}
          borderRadius="full"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.7, 1, 0.7],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            delay: index * 0.15,
          }}
        />
      ))}
    </HStack>
  );
};

export default LoadingOverlay;
