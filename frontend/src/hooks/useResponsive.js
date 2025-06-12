import { useBreakpointValue, useMediaQuery } from '@chakra-ui/react';
import { useState, useEffect } from 'react';

// Custom responsive hook that provides enhanced breakpoint utilities
export const useResponsive = () => {
  const [screenSize, setScreenSize] = useState('md');
  
  // Chakra UI breakpoints
  const [isMobile] = useMediaQuery('(max-width: 768px)');
  const [isTablet] = useMediaQuery('(min-width: 769px) and (max-width: 1024px)');
  const [isDesktop] = useMediaQuery('(min-width: 1025px)');
  const [isLargeDesktop] = useMediaQuery('(min-width: 1440px)');

  // Enhanced breakpoint detection
  useEffect(() => {
    if (isMobile) setScreenSize('mobile');
    else if (isTablet) setScreenSize('tablet');
    else if (isLargeDesktop) setScreenSize('xl');
    else if (isDesktop) setScreenSize('desktop');
  }, [isMobile, isTablet, isDesktop, isLargeDesktop]);

  // Responsive value helper
  const getValue = (values) => {
    if (typeof values === 'object') {
      return values[screenSize] || values.base || values.md;
    }
    return values;
  };

  // Grid columns based on screen size
  const gridCols = useBreakpointValue({
    base: 1,
    sm: 2,
    md: 2,
    lg: 3,
    xl: 4
  });

  // Container max width
  const containerMaxW = useBreakpointValue({
    base: '100%',
    sm: '540px',
    md: '720px',
    lg: '960px',
    xl: '1200px',
    '2xl': '1400px'
  });

  // Padding values
  const containerPadding = useBreakpointValue({
    base: 4,
    sm: 6,
    md: 8,
    lg: 12
  });

  // Font sizes
  const headingSize = useBreakpointValue({
    base: 'lg',
    sm: 'xl',
    md: '2xl',
    lg: '3xl'
  });

  const bodySize = useBreakpointValue({
    base: 'sm',
    sm: 'md',
    md: 'md',
    lg: 'lg'
  });

  // Spacing values
  const spacing = useBreakpointValue({
    base: 4,
    sm: 6,
    md: 8,
    lg: 10
  });

  // Button sizes
  const buttonSize = useBreakpointValue({
    base: 'sm',
    sm: 'md',
    md: 'md',
    lg: 'lg'
  });

  // Card padding
  const cardPadding = useBreakpointValue({
    base: 4,
    sm: 6,
    md: 6,
    lg: 8
  });

  // Modal sizes
  const modalSize = useBreakpointValue({
    base: 'full',
    sm: 'md',
    md: 'lg',
    lg: 'xl'
  });

  return {
    // Device detection
    isMobile,
    isTablet,
    isDesktop,
    isLargeDesktop,
    screenSize,
    
    // Utilities
    getValue,
    
    // Layout values
    gridCols,
    containerMaxW,
    containerPadding,
    spacing,
    cardPadding,
    
    // Typography
    headingSize,
    bodySize,
    
    // Components
    buttonSize,
    modalSize,
    
    // Responsive helpers
    hideOnMobile: { base: 'none', md: 'block' },
    hideOnDesktop: { base: 'block', md: 'none' },
    showOnTabletUp: { base: 'none', sm: 'block' },
    showOnDesktopUp: { base: 'none', lg: 'block' }
  };
};

// Hook for optimized performance on different devices
export const usePerformanceMode = () => {
  const { isMobile, isTablet } = useResponsive();
  
  return {
    // Reduce animations on mobile for better performance
    shouldReduceMotion: isMobile,
    
    // Lazy loading threshold
    lazyLoadThreshold: isMobile ? '100px' : '200px',
    
    // Image quality
    imageQuality: isMobile ? 'medium' : 'high',
    
    // Chart performance
    chartAnimationDuration: isMobile ? 500 : 1000,
    
    // Table pagination
    defaultPageSize: isMobile ? 5 : (isTablet ? 10 : 20),
    
    // Virtualization threshold
    virtualizationThreshold: isMobile ? 50 : 100
  };
};

// Hook for touch-friendly interactions
export const useTouchOptimization = () => {
  const { isMobile, isTablet } = useResponsive();
  const isTouchDevice = isMobile || isTablet;
  
  return {
    isTouchDevice,
    
    // Touch-friendly sizes
    minTouchTarget: isTouchDevice ? '44px' : '32px',
    touchPadding: isTouchDevice ? 4 : 2,
    
    // Hover states (disabled on touch)
    hoverProps: isTouchDevice ? {} : {
      _hover: { transform: 'translateY(-2px)' }
    },
    
    // Touch gestures
    enableSwipeGestures: isTouchDevice,
    enablePullToRefresh: isMobile,
    
    // Scroll behavior
    scrollBehavior: isTouchDevice ? 'auto' : 'smooth'
  };
};
