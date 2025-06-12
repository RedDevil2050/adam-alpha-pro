import React from 'react';
import { Box, useColorModeValue } from '@chakra-ui/react';
import { motion } from 'framer-motion';

const AnimatedBackground = ({ children }) => {
  const bgGradient = useColorModeValue(
    'linear(to-br, blue.50, purple.50, teal.50)',
    'linear(to-br, gray.900, blue.900, purple.900)'
  );

  const FloatingOrb = ({ delay = 0, duration = 20, size = '200px', opacity = 0.1 }) => (
    <motion.div
      style={{
        position: 'absolute',
        width: size,
        height: size,
        background: useColorModeValue(
          'radial-gradient(circle, rgba(66, 165, 245, 0.3) 0%, transparent 70%)',
          'radial-gradient(circle, rgba(66, 165, 245, 0.2) 0%, transparent 70%)'
        ),
        borderRadius: '50%',
        filter: 'blur(1px)',
        opacity,
      }}
      animate={{
        x: [0, 100, 0],
        y: [0, -100, 0],
        scale: [1, 1.2, 1],
      }}
      transition={{
        duration,
        repeat: Infinity,
        delay,
        ease: 'easeInOut',
      }}
    />
  );

  return (
    <Box
      position="relative"
      minH="100vh"
      bgGradient={bgGradient}
      overflow="hidden"
    >
      {/* Floating orbs for visual appeal */}
      <Box position="absolute" top="10%" left="10%" zIndex={0}>
        <FloatingOrb delay={0} duration={15} size="150px" opacity={0.1} />
      </Box>
      <Box position="absolute" top="20%" right="15%" zIndex={0}>
        <FloatingOrb delay={5} duration={20} size="200px" opacity={0.08} />
      </Box>
      <Box position="absolute" bottom="20%" left="20%" zIndex={0}>
        <FloatingOrb delay={10} duration={25} size="180px" opacity={0.12} />
      </Box>
      <Box position="absolute" bottom="10%" right="10%" zIndex={0}>
        <FloatingOrb delay={15} duration={18} size="120px" opacity={0.15} />
      </Box>

      {/* Content */}
      <Box position="relative" zIndex={1}>
        {children}
      </Box>
    </Box>
  );
};

export default AnimatedBackground;
