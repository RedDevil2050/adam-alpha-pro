import { useState, useEffect } from 'react';
import { useColorMode } from '@chakra-ui/react';

const THEME_STORAGE_KEY = 'zion-theme-preference';
const THEME_ACCENT_KEY = 'zion-accent-color';

// Available accent colors
export const ACCENT_COLORS = {
  blue: {
    name: 'Ocean Blue',
    primary: '#3182CE',
    secondary: '#2B6CB0',
    gradient: 'linear(to-r, blue.400, blue.600)'
  },
  purple: {
    name: 'Royal Purple',
    primary: '#805AD5',
    secondary: '#6B46C1',
    gradient: 'linear(to-r, purple.400, purple.600)'
  },
  teal: {
    name: 'Emerald Teal',
    primary: '#319795',
    secondary: '#2C7A7B',
    gradient: 'linear(to-r, teal.400, teal.600)'
  },
  green: {
    name: 'Forest Green',
    primary: '#38A169',
    secondary: '#2F855A',
    gradient: 'linear(to-r, green.400, green.600)'
  },
  orange: {
    name: 'Sunset Orange',
    primary: '#DD6B20',
    secondary: '#C05621',
    gradient: 'linear(to-r, orange.400, orange.600)'
  },
  pink: {
    name: 'Rose Pink',
    primary: '#D53F8C',
    secondary: '#B83280',
    gradient: 'linear(to-r, pink.400, pink.600)'
  },
  red: {
    name: 'Crimson Red',
    primary: '#E53E3E',
    secondary: '#C53030',
    gradient: 'linear(to-r, red.400, red.600)'
  },
  indigo: {
    name: 'Deep Indigo',
    primary: '#667EEA',
    secondary: '#5A67D8',
    gradient: 'linear(to-r, indigo.400, indigo.600)'
  }
};

// Theme persistence hook
export const useThemePersistence = () => {
  const { colorMode, toggleColorMode, setColorMode } = useColorMode();
  const [accentColor, setAccentColorState] = useState('blue');
  const [isLoading, setIsLoading] = useState(true);

  // Load theme preferences from localStorage
  useEffect(() => {
    try {
      const savedColorMode = localStorage.getItem(THEME_STORAGE_KEY);
      const savedAccentColor = localStorage.getItem(THEME_ACCENT_KEY);

      if (savedColorMode && savedColorMode !== colorMode) {
        setColorMode(savedColorMode);
      }

      if (savedAccentColor && ACCENT_COLORS[savedAccentColor]) {
        setAccentColorState(savedAccentColor);
      }
    } catch (error) {
      console.warn('Failed to load theme preferences:', error);
    } finally {
      setIsLoading(false);
    }
  }, [colorMode, setColorMode]);

  // Save color mode when it changes
  useEffect(() => {
    if (!isLoading) {
      try {
        localStorage.setItem(THEME_STORAGE_KEY, colorMode);
      } catch (error) {
        console.warn('Failed to save color mode:', error);
      }
    }
  }, [colorMode, isLoading]);

  // Save accent color when it changes
  const setAccentColor = (newColor) => {
    if (ACCENT_COLORS[newColor]) {
      setAccentColorState(newColor);
      try {
        localStorage.setItem(THEME_ACCENT_KEY, newColor);
        
        // Update CSS custom properties for dynamic theming
        const root = document.documentElement;
        const colors = ACCENT_COLORS[newColor];
        
        root.style.setProperty('--chakra-colors-brand-400', colors.primary);
        root.style.setProperty('--chakra-colors-brand-500', colors.primary);
        root.style.setProperty('--chakra-colors-brand-600', colors.secondary);
        
      } catch (error) {
        console.warn('Failed to save accent color:', error);
      }
    }
  };

  // Reset to default theme
  const resetTheme = () => {
    try {
      localStorage.removeItem(THEME_STORAGE_KEY);
      localStorage.removeItem(THEME_ACCENT_KEY);
      setColorMode('light');
      setAccentColor('blue');
    } catch (error) {
      console.warn('Failed to reset theme:', error);
    }
  };

  // Get current theme info
  const getCurrentTheme = () => {
    return {
      colorMode,
      accentColor,
      accentInfo: ACCENT_COLORS[accentColor],
      isDark: colorMode === 'dark',
      isLight: colorMode === 'light'
    };
  };

  // Export theme configuration
  const exportTheme = () => {
    return {
      colorMode,
      accentColor,
      timestamp: new Date().toISOString(),
      version: '1.0'
    };
  };

  // Import theme configuration
  const importTheme = (themeConfig) => {
    try {
      if (themeConfig.colorMode) {
        setColorMode(themeConfig.colorMode);
      }
      if (themeConfig.accentColor && ACCENT_COLORS[themeConfig.accentColor]) {
        setAccentColor(themeConfig.accentColor);
      }
      return true;
    } catch (error) {
      console.warn('Failed to import theme:', error);
      return false;
    }
  };

  return {
    // Current state
    colorMode,
    accentColor,
    accentInfo: ACCENT_COLORS[accentColor],
    isLoading,
    
    // Actions
    toggleColorMode,
    setColorMode,
    setAccentColor,
    resetTheme,
    
    // Utilities
    getCurrentTheme,
    exportTheme,
    importTheme,
    
    // Available options
    availableAccentColors: ACCENT_COLORS,
    availableColorModes: ['light', 'dark']
  };
};

// Auto theme detection based on system preference and time
export const useAutoTheme = (options = {}) => {
  const { 
    enableTimeBasedSwitching = false,
    lightHour = 6,
    darkHour = 18,
    followSystemPreference = true
  } = options;
  
  const { setColorMode } = useColorMode();
  const [autoMode, setAutoMode] = useState(null);

  useEffect(() => {
    const updateTheme = () => {
      if (!enableTimeBasedSwitching && !followSystemPreference) return;

      let newMode = 'light';

      if (followSystemPreference) {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        newMode = prefersDark ? 'dark' : 'light';
      }

      if (enableTimeBasedSwitching) {
        // Override with time-based switching
        const hour = new Date().getHours();
        newMode = (hour >= darkHour || hour < lightHour) ? 'dark' : 'light';
      }

      if (newMode !== autoMode) {
        setAutoMode(newMode);
        setColorMode(newMode);
      }
    };

    // Initial check
    updateTheme();

    // Set up listeners
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemChange = () => {
      if (followSystemPreference && !enableTimeBasedSwitching) {
        updateTheme();
      }
    };

    // Time-based interval
    let timeInterval;
    if (enableTimeBasedSwitching) {
      timeInterval = setInterval(updateTheme, 60000); // Check every minute
    }

    mediaQuery.addEventListener('change', handleSystemChange);

    return () => {
      mediaQuery.removeEventListener('change', handleSystemChange);
      if (timeInterval) clearInterval(timeInterval);
    };
  }, [
    autoMode,
    setColorMode,
    enableTimeBasedSwitching,
    lightHour,
    darkHour,
    followSystemPreference
  ]);

  return {
    autoMode,
    isAutoEnabled: enableTimeBasedSwitching || followSystemPreference
  };
};

// Theme analytics and usage tracking
export const useThemeAnalytics = () => {
  const [themeUsage, setThemeUsage] = useState({});

  const trackThemeChange = (from, to, type = 'manual') => {
    const event = {
      timestamp: new Date().toISOString(),
      from,
      to,
      type, // 'manual', 'auto', 'system'
      sessionId: getSessionId()
    };

    // Update usage stats
    setThemeUsage(prev => ({
      ...prev,
      [to]: (prev[to] || 0) + 1,
      lastChanged: event.timestamp,
      totalChanges: (prev.totalChanges || 0) + 1
    }));

    // Could send to analytics service
    if (process.env.NODE_ENV === 'production') {
      // sendToAnalytics('theme_change', event);
    }
  };

  const getSessionId = () => {
    let sessionId = sessionStorage.getItem('theme-session-id');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('theme-session-id', sessionId);
    }
    return sessionId;
  };

  return {
    themeUsage,
    trackThemeChange
  };
};
