import { useEffect, useRef, useState } from 'react';
import { useToast } from '@chakra-ui/react';

// Hook for keyboard navigation
export const useKeyboardNavigation = (items = [], options = {}) => {
  const [currentIndex, setCurrentIndex] = useState(options.initialIndex || 0);
  const [isNavigating, setIsNavigating] = useState(false);
  const containerRef = useRef(null);

  const {
    loop = true,
    horizontal = false,
    onSelect,
    onEscape,
    autoFocus = false
  } = options;

  useEffect(() => {
    if (!isNavigating) return;

    const handleKeyDown = (event) => {
      const { key } = event;
      
      switch (key) {
        case horizontal ? 'ArrowLeft' : 'ArrowUp':
          event.preventDefault();
          setCurrentIndex(prev => {
            if (prev === 0) {
              return loop ? items.length - 1 : 0;
            }
            return prev - 1;
          });
          break;

        case horizontal ? 'ArrowRight' : 'ArrowDown':
          event.preventDefault();
          setCurrentIndex(prev => {
            if (prev === items.length - 1) {
              return loop ? 0 : items.length - 1;
            }
            return prev + 1;
          });
          break;

        case 'Enter':
        case ' ':
          event.preventDefault();
          if (onSelect && items[currentIndex]) {
            onSelect(items[currentIndex], currentIndex);
          }
          break;

        case 'Escape':
          event.preventDefault();
          setIsNavigating(false);
          if (onEscape) onEscape();
          break;

        case 'Home':
          event.preventDefault();
          setCurrentIndex(0);
          break;

        case 'End':
          event.preventDefault();
          setCurrentIndex(items.length - 1);
          break;

        default:
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isNavigating, currentIndex, items, loop, horizontal, onSelect, onEscape]);

  useEffect(() => {
    if (autoFocus && containerRef.current) {
      containerRef.current.focus();
    }
  }, [autoFocus]);

  return {
    currentIndex,
    setCurrentIndex,
    isNavigating,
    setIsNavigating,
    containerRef,
    
    // Helper functions
    moveTo: (index) => {
      if (index >= 0 && index < items.length) {
        setCurrentIndex(index);
      }
    },
    
    moveNext: () => {
      setCurrentIndex(prev => {
        if (prev === items.length - 1) {
          return loop ? 0 : items.length - 1;
        }
        return prev + 1;
      });
    },
    
    movePrevious: () => {
      setCurrentIndex(prev => {
        if (prev === 0) {
          return loop ? items.length - 1 : 0;
        }
        return prev - 1;
      });
    }
  };
};

// Hook for focus management
export const useFocusManagement = () => {
  const focusRef = useRef(null);
  const previousFocusRef = useRef(null);

  const trapFocus = (element) => {
    if (!element) return;

    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    element.addEventListener('keydown', handleTabKey);
    firstElement?.focus();

    return () => {
      element.removeEventListener('keydown', handleTabKey);
    };
  };

  const saveFocus = () => {
    previousFocusRef.current = document.activeElement;
  };

  const restoreFocus = () => {
    if (previousFocusRef.current && previousFocusRef.current.focus) {
      previousFocusRef.current.focus();
    }
  };

  const focusElement = (element) => {
    if (element && element.focus) {
      element.focus();
    }
  };

  return {
    focusRef,
    trapFocus,
    saveFocus,
    restoreFocus,
    focusElement
  };
};

// Hook for screen reader announcements
export const useScreenReader = () => {
  const toast = useToast();
  const [announcements, setAnnouncements] = useState([]);

  const announce = (message, priority = 'polite') => {
    const announcement = {
      id: Date.now(),
      message,
      priority,
      timestamp: new Date()
    };

    setAnnouncements(prev => [...prev, announcement]);

    // Also use toast for visual feedback
    if (priority === 'assertive') {
      toast({
        title: message,
        status: 'info',
        duration: 3000,
        isClosable: true
      });
    }

    // Create or update live region
    let liveRegion = document.getElementById(`live-region-${priority}`);
    if (!liveRegion) {
      liveRegion = document.createElement('div');
      liveRegion.id = `live-region-${priority}`;
      liveRegion.setAttribute('aria-live', priority);
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.style.position = 'absolute';
      liveRegion.style.left = '-10000px';
      liveRegion.style.width = '1px';
      liveRegion.style.height = '1px';
      liveRegion.style.overflow = 'hidden';
      document.body.appendChild(liveRegion);
    }

    liveRegion.textContent = message;

    // Clean up old announcements
    setTimeout(() => {
      setAnnouncements(prev => 
        prev.filter(a => a.id !== announcement.id)
      );
    }, 5000);
  };

  const announceError = (message) => {
    announce(`Error: ${message}`, 'assertive');
  };

  const announceSuccess = (message) => {
    announce(`Success: ${message}`, 'polite');
  };

  const announceLoading = (message) => {
    announce(`Loading: ${message}`, 'polite');
  };

  return {
    announce,
    announceError,
    announceSuccess,
    announceLoading,
    announcements
  };
};

// Hook for reduced motion preferences
export const useReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return {
    prefersReducedMotion,
    
    // Animation values based on preference
    animationDuration: prefersReducedMotion ? 0 : undefined,
    transitionDuration: prefersReducedMotion ? '0ms' : undefined,
    
    // Conditional animation props
    getAnimationProps: (animationProps = {}) => {
      if (prefersReducedMotion) {
        return { ...animationProps, animate: animationProps.initial };
      }
      return animationProps;
    }
  };
};

// ARIA label helpers
export const getAriaLabel = (type, context = {}) => {
  const labels = {
    // Navigation
    'main-nav': 'Main navigation',
    'breadcrumb': 'Breadcrumb navigation',
    'pagination': 'Pagination navigation',
    
    // Actions
    'close': 'Close',
    'menu': 'Menu',
    'search': 'Search',
    'filter': 'Filter',
    'sort': 'Sort',
    
    // Status
    'loading': `Loading ${context.item || 'content'}`,
    'error': `Error loading ${context.item || 'content'}`,
    'success': `Successfully loaded ${context.item || 'content'}`,
    
    // Data
    'chart': `${context.type || 'Chart'} showing ${context.description || 'data'}`,
    'table': `Table with ${context.rows || 0} rows and ${context.columns || 0} columns`,
    
    // Forms
    'required': 'Required field',
    'optional': 'Optional field',
    'invalid': 'Invalid input'
  };

  return labels[type] || '';
};

export default {
  useKeyboardNavigation,
  useFocusManagement,
  useScreenReader,
  useReducedMotion,
  getAriaLabel
};
