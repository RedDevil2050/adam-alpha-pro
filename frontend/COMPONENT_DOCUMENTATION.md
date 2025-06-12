# Zion Market Analysis Platform - Component Documentation

## Overview

The Zion frontend has been enhanced with a modern, loveable design system featuring beautiful animations, real-time data displays, and an intuitive user experience. This documentation covers all the custom components and utilities created for the platform.

## 🎨 Design System

### Theme (`loveableTheme.js`)

A comprehensive Chakra UI theme with:

- **Custom Colors**: Brand palette with gradients and semantic colors
- **Typography**: Modern font stack with responsive sizing
- **Component Variants**: Enhanced button, card, and input styles
- **Animations**: Predefined motion configurations
- **Responsive Breakpoints**: Mobile-first design system

```javascript
import loveableTheme from './theme/loveableTheme';

// Usage in App.js
<ChakraProvider theme={loveableTheme}>
  {/* Your app */}
</ChakraProvider>
```

## 🌟 Core Components

### AnimatedBackground (`components/common/AnimatedBackground.js`)

Creates floating orbs with gradient backgrounds and smooth animations.

**Props:**

- `variant` (string): 'default' | 'subtle' | 'vibrant'
- `particleCount` (number): Number of floating orbs (default: 6)
- `speed` (number): Animation speed multiplier (default: 1)

**Usage:**

```jsx
<AnimatedBackground variant="subtle" particleCount={8} />
```

### RealTimeAnalysisStream (`components/analysis/RealTimeAnalysisStream.js`)

Displays live analysis progress with agent execution visualization.

**Features:**

- WebSocket connection for real-time updates
- Agent execution timeline
- Progress indicators
- Analysis result display

**Props:**

- `symbol` (string): Stock symbol to analyze
- `onComplete` (function): Callback when analysis completes
- `autoStart` (boolean): Start analysis automatically

### MarketPulse (`components/dashboard/MarketPulse.js`)

Real-time market data display with Indian market indices.

**Features:**

- Live market data feeds
- Price change indicators
- Market status (open/closed)
- Interactive charts

**Props:**

- `symbols` (array): Array of market symbols
- `refreshInterval` (number): Data refresh interval in ms
- `showCharts` (boolean): Display mini charts

### FloatingActionButton (`components/common/FloatingActionButton.js`)

Expandable FAB with quick actions.

**Features:**

- Smooth expand/collapse animations
- Customizable action items
- Keyboard navigation support
- Touch-friendly interactions

**Props:**

- `actions` (array): Array of action objects
- `position` (string): 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
- `size` (string): 'sm' | 'md' | 'lg'

### SystemHealthWidget (`components/widgets/SystemHealthWidget.js`)

Animated system metrics display.

**Features:**

- Real-time health metrics
- Animated progress bars
- Status indicators
- Performance alerts

### SmartWatchlist (`components/widgets/SmartWatchlist.js`)

Interactive watchlist with alerts and analysis buttons.

**Features:**

- Drag-and-drop reordering
- Price alerts configuration
- Quick analysis access
- Real-time price updates

### NotificationCenter (`components/common/NotificationCenter.js`)

Bell notifications with real-time updates.

**Features:**

- WebSocket notifications
- Priority-based categorization
- Filtering and search
- Action buttons (star, delete, mark as read)
- Screen reader announcements

### LoadingOverlay (`components/common/LoadingOverlay.js`)

Beautiful loading animations for different use cases.

**Types:**

- `pulse`: Pulsing animation
- `spinner`: Rotating spinner
- `skeleton`: Skeleton loading
- `dots`: Animated dots
- `wave`: Wave animation

### ErrorBoundary (`components/common/ErrorBoundary.js`)

Comprehensive error handling with user-friendly interfaces.

**Features:**

- Component-level error catching
- Technical details collapsible view
- Recovery actions
- Error reporting integration

## 📱 Layout Components

### MainLayout (`components/layout/MainLayout.js`)

Enhanced main application layout with:

- Responsive navigation
- API status monitoring
- Notification center integration
- Theme switching
- Mobile-friendly drawer

### LandingPage (`pages/LandingPage.js`)

Marketing page with:

- Hero section with animations
- Feature showcase
- Statistics display
- Call-to-action buttons
- Responsive design

## 🔧 Utilities & Hooks

### useResponsive (`hooks/useResponsive.js`)

Comprehensive responsive design utilities.

**Features:**

- Device detection
- Responsive values
- Grid configurations
- Touch optimizations
- Performance modes

**Usage:**

```javascript
const { isMobile, gridCols, containerMaxW } = useResponsive();
```

### useAccessibility (`hooks/useAccessibility.js`)

Accessibility features and helpers.

**Features:**

- Keyboard navigation
- Focus management
- Screen reader announcements
- Reduced motion detection
- ARIA label helpers

**Usage:**

```javascript
const { announce, useKeyboardNavigation } = useAccessibility();
announce('Data loaded successfully');
```

### useThemePersistence (`hooks/useThemePersistence.js`)

Theme switching with persistence.

**Features:**

- Color mode persistence
- Accent color selection
- Auto theme detection
- Theme analytics
- Import/export themes

**Usage:**

```javascript
const { accentColor, setAccentColor, toggleColorMode } = useThemePersistence();
```

### Performance Utilities (`utils/performance.js`)

Optimization utilities for better performance.

**Features:**

- Lazy loading with retry
- Virtual scrolling
- Progressive image loading
- Bundle analysis
- Performance monitoring

**Usage:**

```javascript
const LazyComponent = createLazyComponent(() => import('./HeavyComponent'));

// Virtual list for large datasets
<VirtualList
  items={largeDataset}
  renderItem={(item) => <ItemComponent item={item} />}
  itemHeight={60}
/>
```

## 🎯 Integration Examples

### Adding Real-time Features

```javascript
// WebSocket connection example
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws/market-data');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateMarketData(data);
  };
  
  return () => ws.close();
}, []);
```

### Implementing Animations

```javascript
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

<MotionBox
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
  whileHover={{ scale: 1.05 }}
>
  Content with animations
</MotionBox>
```

### Accessibility Implementation

```javascript
import { useKeyboardNavigation, useScreenReader } from '../hooks/useAccessibility';

const Component = () => {
  const { announce } = useScreenReader();
  const { currentIndex, containerRef } = useKeyboardNavigation(items);
  
  const handleAction = () => {
    announce('Action completed successfully');
  };
  
  return (
    <Box ref={containerRef} tabIndex={0}>
      {/* Keyboard navigable content */}
    </Box>
  );
};
```

## 🚀 Performance Best Practices

1. **Lazy Loading**: Use `createLazyComponent` for route-level components
2. **Virtual Scrolling**: Implement for lists with >100 items
3. **Image Optimization**: Use `ProgressiveImage` for dynamic images
4. **Bundle Splitting**: Code split by feature/route
5. **Memoization**: Use React.memo for expensive components

## 📊 Monitoring & Analytics

The platform includes built-in monitoring for:

- Component render times
- Error tracking
- User interaction analytics
- Performance metrics
- Theme usage statistics

## 🔒 Security Considerations

- All API calls include authentication headers
- Input validation on all forms
- XSS protection through proper sanitization
- CSRF protection for state-changing operations

## 🧪 Testing

Components are designed to be testable with:

- Prop-driven behavior
- Accessible selectors
- Mocked WebSocket connections
- Performance benchmarks

## 📝 Contributing

When adding new components:

1. Follow the established naming conventions
2. Include proper TypeScript types
3. Add accessibility features
4. Implement responsive design
5. Include error boundaries
6. Add performance monitoring
7. Write comprehensive documentation

## 🔗 Resources

- [Chakra UI Documentation](https://chakra-ui.com/)
- [Framer Motion Guide](https://www.framer.com/motion/)
- [React Query Documentation](https://react-query.tanstack.com/)
- [Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

For questions or contributions, please refer to the project's GitHub repository or contact the development team.
