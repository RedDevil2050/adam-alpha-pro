import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  useColorModeValue,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

const FloatingActionButton = ({ onClick, isVisible = true }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const shadowColor = useColorModeValue('rgba(0,0,0,0.1)', 'rgba(0,0,0,0.3)');

  const quickActions = [
    { label: 'Quick Analysis', action: () => onClick('analyze'), icon: '📊' },
    { label: 'Market Alert', action: () => onClick('alert'), icon: '🔔' },
    { label: 'Portfolio View', action: () => onClick('portfolio'), icon: '💼' },
    { label: 'Watchlist', action: () => onClick('watchlist'), icon: '⭐' },
  ];

  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ 
        scale: isVisible ? 1 : 0, 
        opacity: isVisible ? 1 : 0 
      }}
      transition={{ duration: 0.3, type: "spring" }}
      style={{
        position: 'fixed',
        bottom: '2rem',
        right: '2rem',
        zIndex: 1000,
      }}
    >
      <VStack spacing={3} align="end">
        {/* Quick Actions */}
        {isExpanded && (
          <VStack spacing={2} align="end">
            {quickActions.map((action, index) => (
              <motion.div
                key={action.label}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <HStack
                  onClick={action.action}
                  cursor="pointer"
                  bg={bgColor}
                  py={2}
                  px={4}
                  borderRadius="full"
                  boxShadow={`0 4px 20px ${shadowColor}`}
                  border="1px"
                  borderColor={useColorModeValue('gray.200', 'gray.700')}
                  _hover={{
                    transform: 'translateY(-2px)',
                    boxShadow: `0 8px 25px ${shadowColor}`,
                    borderColor: 'blue.300'
                  }}
                  transition="all 0.2s"
                  spacing={3}
                >
                  <Text fontSize="sm" fontWeight="medium">
                    {action.label}
                  </Text>
                  <Text fontSize="lg">{action.icon}</Text>
                </HStack>
              </motion.div>
            ))}
          </VStack>
        )}

        {/* Main FAB */}
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Flex
            onClick={() => setIsExpanded(!isExpanded)}
            cursor="pointer"
            bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            color="white"
            w={16}
            h={16}
            borderRadius="full"
            align="center"
            justify="center"
            boxShadow={`0 8px 30px ${shadowColor}`}
            _hover={{
              transform: 'translateY(-2px)',
              boxShadow: `0 12px 35px ${shadowColor}`,
            }}
            transition="all 0.3s"
          >
            <motion.div
              animate={{ rotate: isExpanded ? 45 : 0 }}
              transition={{ duration: 0.3 }}
            >
              <Text fontSize="xl" fontWeight="bold">
                +
              </Text>
            </motion.div>
          </Flex>
        </motion.div>
      </VStack>
    </motion.div>
  );
};

export default FloatingActionButton;
