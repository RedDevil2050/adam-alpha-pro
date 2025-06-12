import React, { Suspense, lazy, useCallback, useMemo } from 'react';
import { Box, Spinner, Center, Text, VStack } from '@chakra-ui/react';
import { useInView } from 'react-intersection-observer';
import { usePerformanceMode } from '../hooks/useResponsive';

// Enhanced lazy loading with retry mechanism
export const createLazyComponent = (importFunc, options = {}) => {
  const { 
    fallback = <ComponentLoader />,
    retryDelay = 1000,
    maxRetries = 3 
  } = options;

  let retryCount = 0;

  const loadComponent = () => {
    return importFunc().catch((error) => {
      if (retryCount < maxRetries) {
        retryCount++;
        console.warn(`Failed to load component. Retrying... (${retryCount}/${maxRetries})`);
        return new Promise((resolve) => {
          setTimeout(() => resolve(loadComponent()), retryDelay * retryCount);
        });
      }
      throw error;
    });
  };

  return lazy(loadComponent);
};

// Default loading component
const ComponentLoader = ({ message = "Loading component..." }) => (
  <Center p={8}>
    <VStack spacing={3}>
      <Spinner size="lg" color="brand.500" thickness="3px" />
      <Text fontSize="sm" color="gray.500">{message}</Text>
    </VStack>
  </Center>
);

// Error boundary for lazy components
class LazyComponentErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Lazy component error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box p={6} textAlign="center">
          <Text color="red.500" fontWeight="bold">
            Failed to load component
          </Text>
          <Text fontSize="sm" color="gray.500" mt={2}>
            Please refresh the page or try again later
          </Text>
        </Box>
      );
    }

    return this.props.children;
  }
}

// Lazy wrapper with error boundary
export const LazyWrapper = ({ children, fallback, ...props }) => (
  <LazyComponentErrorBoundary>
    <Suspense fallback={fallback || <ComponentLoader />} {...props}>
      {children}
    </Suspense>
  </LazyComponentErrorBoundary>
);

// Intersection-based lazy loading
export const LazyIntersectionWrapper = ({ 
  children, 
  fallback,
  threshold = 0.1,
  rootMargin = '50px',
  triggerOnce = true,
  ...props 
}) => {
  const { lazyLoadThreshold } = usePerformanceMode();
  const { ref, inView } = useInView({
    threshold,
    rootMargin: lazyLoadThreshold || rootMargin,
    triggerOnce
  });

  return (
    <Box ref={ref} {...props}>
      {inView ? (
        <LazyWrapper fallback={fallback}>
          {children}
        </LazyWrapper>
      ) : (
        fallback || <ComponentLoader message="Preparing component..." />
      )}
    </Box>
  );
};

// Virtual scrolling for large lists
export const VirtualList = ({ 
  items, 
  renderItem, 
  itemHeight = 60, 
  containerHeight = 400,
  overscan = 5 
}) => {
  const [scrollTop, setScrollTop] = React.useState(0);
  const { virtualizationThreshold } = usePerformanceMode();

  const visibleItems = useMemo(() => {
    if (items.length <= virtualizationThreshold) {
      return items.map((item, index) => ({ item, index }));
    }

    const containerTop = scrollTop;
    const containerBottom = scrollTop + containerHeight;
    
    const startIndex = Math.max(0, Math.floor(containerTop / itemHeight) - overscan);
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil(containerBottom / itemHeight) + overscan
    );

    const visibleItems = [];
    for (let i = startIndex; i <= endIndex; i++) {
      visibleItems.push({ item: items[i], index: i });
    }

    return visibleItems;
  }, [items, scrollTop, containerHeight, itemHeight, overscan, virtualizationThreshold]);

  const totalHeight = items.length * itemHeight;

  const handleScroll = useCallback((e) => {
    setScrollTop(e.target.scrollTop);
  }, []);

  // Don't virtualize for small lists
  if (items.length <= virtualizationThreshold) {
    return (
      <Box maxH={containerHeight} overflowY="auto" onScroll={handleScroll}>
        {items.map((item, index) => (
          <Box key={index} h={`${itemHeight}px`}>
            {renderItem(item, index)}
          </Box>
        ))}
      </Box>
    );
  }

  return (
    <Box 
      maxH={containerHeight} 
      overflowY="auto" 
      onScroll={handleScroll}
      position="relative"
    >
      <Box h={`${totalHeight}px`} position="relative">
        {visibleItems.map(({ item, index }) => (
          <Box
            key={index}
            position="absolute"
            top={`${index * itemHeight}px`}
            w="100%"
            h={`${itemHeight}px`}
          >
            {renderItem(item, index)}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

// Progressive image loading
export const ProgressiveImage = ({ 
  src, 
  placeholder, 
  alt, 
  onLoad, 
  onError,
  ...props 
}) => {
  const [imageSrc, setImageSrc] = React.useState(placeholder);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const { imageQuality } = usePerformanceMode();

  React.useEffect(() => {
    const img = new Image();
    
    img.onload = () => {
      setImageSrc(src);
      setLoading(false);
      onLoad && onLoad();
    };
    
    img.onerror = () => {
      setError(true);
      setLoading(false);
      onError && onError();
    };

    // Adjust image quality based on performance mode
    const optimizedSrc = imageQuality === 'medium' 
      ? src.replace(/\.(jpg|jpeg|png)$/, '_compressed.$1')
      : src;
      
    img.src = optimizedSrc;
  }, [src, imageQuality, onLoad, onError]);

  if (error) {
    return (
      <Box {...props} bg="gray.100" display="flex" alignItems="center" justifyContent="center">
        <Text fontSize="sm" color="gray.500">Failed to load image</Text>
      </Box>
    );
  }

  return (
    <Box position="relative" {...props}>
      <img
        src={imageSrc}
        alt={alt}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          opacity: loading ? 0.6 : 1,
          transition: 'opacity 0.3s ease'
        }}
      />
      {loading && (
        <Center
          position="absolute"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
        >
          <Spinner size="sm" />
        </Center>
      )}
    </Box>
  );
};

// Code splitting utilities
export const createChunkedComponent = (components) => {
  const ChunkedComponent = ({ component: componentName, ...props }) => {
    const Component = components[componentName];
    
    if (!Component) {
      console.warn(`Component "${componentName}" not found in chunk`);
      return <Text color="red.500">Component not found</Text>;
    }

    return <Component {...props} />;
  };

  return ChunkedComponent;
};

// Bundle size analyzer (development only)
export const analyzeBundleSize = () => {
  if (process.env.NODE_ENV !== 'production') {
    const chunks = [];
    
    // This would analyze webpack chunks in a real implementation
    console.group('Bundle Analysis');
    console.log('Analyzing bundle size...');
    console.log('Chunks loaded:', chunks.length);
    console.groupEnd();
  }
};

// Performance monitoring hook
export const usePerformanceMonitoring = (componentName) => {
  React.useEffect(() => {
    const startTime = performance.now();
    
    return () => {
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      if (renderTime > 100) { // Log slow renders
        console.warn(`Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`);
      }
      
      // Send to monitoring service in production
      if (process.env.NODE_ENV === 'production' && renderTime > 500) {
        // sendPerformanceMetric(componentName, renderTime);
      }
    };
  });
};

export default {
  createLazyComponent,
  LazyWrapper,
  LazyIntersectionWrapper,
  VirtualList,
  ProgressiveImage,
  createChunkedComponent,
  analyzeBundleSize,
  usePerformanceMonitoring
};
