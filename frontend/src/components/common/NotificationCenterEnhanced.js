import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  IconButton,
  VStack,
  HStack,
  Text,
  Badge,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  PopoverHeader,
  Divider,
  Button,
  useColorModeValue,
  useDisclosure,
  Avatar,
  Spinner,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  useToast,
  Tooltip
} from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, 
  X, 
  Check, 
  AlertTriangle, 
  Info, 
  TrendingUp, 
  TrendingDown,
  Settings,
  Archive,
  Star,
  Clock,
  Filter,
  MoreVertical
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useScreenReader } from '../../hooks/useAccessibility';

const MotionBox = motion(Box);

// Enhanced notification types
const NOTIFICATION_TYPES = {
  MARKET_ALERT: {
    icon: TrendingUp,
    color: 'blue',
    priority: 'high',
    category: 'Market'
  },
  PRICE_TARGET: {
    icon: TrendingDown,
    color: 'red',
    priority: 'high',
    category: 'Trading'
  },
  ANALYSIS_COMPLETE: {
    icon: Check,
    color: 'green',
    priority: 'medium',
    category: 'Analysis'
  },
  SYSTEM_UPDATE: {
    icon: Info,
    color: 'blue',
    priority: 'low',
    category: 'System'
  },
  WARNING: {
    icon: AlertTriangle,
    color: 'orange',
    priority: 'high',
    category: 'Alert'
  },
  PORTFOLIO_UPDATE: {
    icon: TrendingUp,
    color: 'purple',
    priority: 'medium',
    category: 'Portfolio'
  }
};

const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const { isOpen, onToggle, onClose } = useDisclosure();
  const { announce } = useScreenReader();
  const toast = useToast();
  const wsRef = useRef(null);
  
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');

  // Simulated notifications for demo
  useEffect(() => {
    const sampleNotifications = [
      {
        id: '1',
        type: 'MARKET_ALERT',
        title: 'NIFTY 50 Alert',
        message: 'NIFTY 50 has crossed above 18,500 resistance level',
        timestamp: new Date(Date.now() - 5 * 60 * 1000),
        read: false,
        starred: false,
        actionUrl: '/analysis/NIFTY'
      },
      {
        id: '2',
        type: 'ANALYSIS_COMPLETE',
        title: 'Analysis Complete',
        message: 'Technical analysis for RELIANCE is now available',
        timestamp: new Date(Date.now() - 30 * 60 * 1000),
        read: false,
        starred: true,
        actionUrl: '/analysis/RELIANCE'
      },
      {
        id: '3',
        type: 'PORTFOLIO_UPDATE',
        title: 'Portfolio Performance',
        message: 'Your portfolio gained 2.5% today',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
        read: true,
        starred: false,
        actionUrl: '/portfolio'
      },
      {
        id: '4',
        type: 'PRICE_TARGET',
        title: 'Price Target Hit',
        message: 'TCS reached your target price of ₹3,500',
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
        read: false,
        starred: false,
        actionUrl: '/analysis/TCS'
      }
    ];
    
    setNotifications(sampleNotifications);
    
    // Announce new notifications
    const unreadCount = sampleNotifications.filter(n => !n.read).length;
    if (unreadCount > 0) {
      announce(`You have ${unreadCount} new notifications`);
    }
  }, [announce]);

  // WebSocket connection for real-time notifications
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket(`ws://localhost:8000/ws/notifications`);
        
        wsRef.current.onmessage = (event) => {
          const notification = JSON.parse(event.data);
          addNotification(notification);
        };
        
        wsRef.current.onerror = () => {
          console.warn('Notification WebSocket error - using polling fallback');
        };
        
        wsRef.current.onclose = () => {
          // Reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000);
        };
      } catch (error) {
        console.warn('WebSocket not available, using polling');
        // Fallback to polling every 30 seconds
        const interval = setInterval(fetchNotifications, 30000);
        return () => clearInterval(interval);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const fetchNotifications = async () => {
    setIsLoading(true);
    try {
      // Simulated API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      // const response = await fetch('/api/notifications');
      // const data = await response.json();
      // setNotifications(data);
    } catch (error) {
      toast({
        title: 'Failed to fetch notifications',
        status: 'error',
        duration: 3000
      });
    } finally {
      setIsLoading(false);
    }
  };

  const addNotification = (notification) => {
    const newNotification = {
      ...notification,
      id: notification.id || Date.now().toString(),
      timestamp: new Date(notification.timestamp || Date.now()),
      read: false,
      starred: false
    };

    setNotifications(prev => [newNotification, ...prev]);
    
    // Announce new notification
    announce(`New notification: ${notification.title}`);
    
    // Show toast for high priority notifications
    if (NOTIFICATION_TYPES[notification.type]?.priority === 'high') {
      toast({
        title: notification.title,
        description: notification.message,
        status: 'info',
        duration: 5000,
        isClosable: true
      });
    }
  };

  const markAsRead = (id) => {
    setNotifications(prev =>
      prev.map(notification =>
        notification.id === id ? { ...notification, read: true } : notification
      )
    );
  };

  const markAllAsRead = () => {
    setNotifications(prev =>
      prev.map(notification => ({ ...notification, read: true }))
    );
    announce('All notifications marked as read');
  };

  const toggleStar = (id) => {
    setNotifications(prev =>
      prev.map(notification =>
        notification.id === id 
          ? { ...notification, starred: !notification.starred }
          : notification
      )
    );
  };

  const deleteNotification = (id) => {
    setNotifications(prev =>
      prev.filter(notification => notification.id !== id)
    );
    announce('Notification deleted');
  };

  const clearAll = () => {
    setNotifications([]);
    announce('All notifications cleared');
  };

  const getFilteredNotifications = () => {
    switch (filter) {
      case 'unread':
        return notifications.filter(n => !n.read);
      case 'starred':
        return notifications.filter(n => n.starred);
      case 'market':
        return notifications.filter(n => 
          NOTIFICATION_TYPES[n.type]?.category === 'Market'
        );
      case 'trading':
        return notifications.filter(n => 
          NOTIFICATION_TYPES[n.type]?.category === 'Trading'
        );
      default:
        return notifications;
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;
  const filteredNotifications = getFilteredNotifications();

  return (
    <Popover 
      isOpen={isOpen} 
      onClose={onClose}
      placement="bottom-end"
      closeOnBlur={true}
    >
      <PopoverTrigger>
        <Box position="relative">
          <Tooltip label="Notifications" placement="bottom">
            <IconButton
              icon={<Bell size={20} />}
              variant="ghost"
              onClick={onToggle}
              aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
              position="relative"
            />
          </Tooltip>
          {unreadCount > 0 && (
            <Badge
              position="absolute"
              top="-2px"
              right="-2px"
              colorScheme="red"
              borderRadius="full"
              minW="20px"
              h="20px"
              display="flex"
              alignItems="center"
              justifyContent="center"
              fontSize="xs"
              fontWeight="bold"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
        </Box>
      </PopoverTrigger>

      <PopoverContent w="400px" bg={bg} borderColor={borderColor} shadow="xl">
        <PopoverHeader p={4} borderBottomWidth="1px">
          <HStack justify="space-between">
            <Text fontWeight="bold" fontSize="lg">
              Notifications
            </Text>
            <HStack spacing={2}>
              {isLoading && <Spinner size="sm" />}
              <Menu>
                <MenuButton
                  as={IconButton}
                  icon={<Filter size={16} />}
                  variant="ghost"
                  size="sm"
                  aria-label="Filter notifications"
                />
                <MenuList>
                  <MenuItem onClick={() => setFilter('all')}>
                    All Notifications
                  </MenuItem>
                  <MenuItem onClick={() => setFilter('unread')}>
                    Unread Only
                  </MenuItem>
                  <MenuItem onClick={() => setFilter('starred')}>
                    Starred
                  </MenuItem>
                  <MenuDivider />
                  <MenuItem onClick={() => setFilter('market')}>
                    Market Alerts
                  </MenuItem>
                  <MenuItem onClick={() => setFilter('trading')}>
                    Trading
                  </MenuItem>
                </MenuList>
              </Menu>
              <Menu>
                <MenuButton
                  as={IconButton}
                  icon={<MoreVertical size={16} />}
                  variant="ghost"
                  size="sm"
                  aria-label="Notification options"
                />
                <MenuList>
                  <MenuItem onClick={markAllAsRead} icon={<Check size={16} />}>
                    Mark All Read
                  </MenuItem>
                  <MenuItem onClick={clearAll} icon={<Archive size={16} />}>
                    Clear All
                  </MenuItem>
                  <MenuDivider />
                  <MenuItem icon={<Settings size={16} />}>
                    Settings
                  </MenuItem>
                </MenuList>
              </Menu>
            </HStack>
          </HStack>
        </PopoverHeader>

        <PopoverBody p={0} maxH="400px" overflowY="auto">
          {filteredNotifications.length === 0 ? (
            <Box p={8} textAlign="center">
              <Text color="gray.500" fontSize="sm">
                {filter === 'all' ? 'No notifications' : `No ${filter} notifications`}
              </Text>
            </Box>
          ) : (
            <VStack spacing={0} align="stretch">
              <AnimatePresence>
                {filteredNotifications.map((notification, index) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={markAsRead}
                    onStar={toggleStar}
                    onDelete={deleteNotification}
                    index={index}
                  />
                ))}
              </AnimatePresence>
            </VStack>
          )}
        </PopoverBody>
      </PopoverContent>
    </Popover>
  );
};

const NotificationItem = ({ notification, onRead, onStar, onDelete, index }) => {
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const typeConfig = NOTIFICATION_TYPES[notification.type] || NOTIFICATION_TYPES.SYSTEM_UPDATE;
  const IconComponent = typeConfig.icon;

  const handleClick = () => {
    if (!notification.read) {
      onRead(notification.id);
    }
    
    if (notification.actionUrl) {
      // Navigate to the action URL
      window.location.href = notification.actionUrl;
    }
  };

  return (
    <MotionBox
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ delay: index * 0.05 }}
    >
      <Box
        p={4}
        borderBottomWidth="1px"
        borderBottomColor="gray.100"
        _hover={{ bg: hoverBg }}
        cursor={notification.actionUrl ? "pointer" : "default"}
        onClick={handleClick}
        position="relative"
      >
        <HStack spacing={3} align="start">
          <Box
            p={2}
            borderRadius="lg"
            bg={`${typeConfig.color}.100`}
            color={`${typeConfig.color}.600`}
            flexShrink={0}
          >
            <IconComponent size={16} />
          </Box>

          <VStack spacing={1} align="start" flex={1} minW={0}>
            <HStack justify="space-between" w="full">
              <Text
                fontWeight={notification.read ? "normal" : "bold"}
                fontSize="sm"
                noOfLines={1}
                color={notification.read ? "gray.600" : "gray.900"}
              >
                {notification.title}
              </Text>
              <HStack spacing={1}>
                {notification.starred && (
                  <Star size={12} fill="currentColor" color="orange.400" />
                )}
                <Text fontSize="xs" color="gray.500">
                  {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
                </Text>
              </HStack>
            </HStack>

            <Text fontSize="xs" color="gray.600" noOfLines={2}>
              {notification.message}
            </Text>

            <HStack spacing={2} mt={2}>
              <Badge
                size="sm"
                colorScheme={typeConfig.color}
                variant="subtle"
              >
                {typeConfig.category}
              </Badge>
              {typeConfig.priority === 'high' && (
                <Badge size="sm" colorScheme="red" variant="outline">
                  High Priority
                </Badge>
              )}
            </HStack>
          </VStack>

          <VStack spacing={1}>
            <IconButton
              icon={<Star size={12} />}
              size="xs"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                onStar(notification.id);
              }}
              color={notification.starred ? "orange.400" : "gray.400"}
              aria-label={notification.starred ? "Unstar" : "Star"}
            />
            <IconButton
              icon={<X size={12} />}
              size="xs"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(notification.id);
              }}
              color="gray.400"
              aria-label="Delete"
            />
          </VStack>
        </HStack>

        {!notification.read && (
          <Box
            position="absolute"
            left={2}
            top="50%"
            transform="translateY(-50%)"
            w={2}
            h={2}
            bg="blue.500"
            borderRadius="full"
          />
        )}
      </Box>
    </MotionBox>
  );
};

export default NotificationCenter;
