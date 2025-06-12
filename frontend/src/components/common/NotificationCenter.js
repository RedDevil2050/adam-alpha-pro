import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  IconButton,
  Badge,
  useColorModeValue,
  useToast,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverHeader,
  PopoverBody,
  PopoverCloseButton,
  Button,
  Divider,
  Avatar,
  Flex,
} from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, X, TrendingUp, TrendingDown, AlertTriangle, Info } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const MotionBox = motion(Box);

const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([
    {
      id: 1,
      type: 'price_alert',
      title: 'Price Alert: AAPL',
      message: 'Apple Inc. has reached your target price of $175.00',
      timestamp: new Date(Date.now() - 5 * 60 * 1000),
      read: false,
      icon: TrendingUp,
      color: 'green'
    },
    {
      id: 2,
      type: 'analysis_complete',
      title: 'Analysis Complete',
      message: 'Your comprehensive analysis for TSLA is ready',
      timestamp: new Date(Date.now() - 15 * 60 * 1000),
      read: false,
      icon: Info,
      color: 'blue'
    },
    {
      id: 3,
      type: 'risk_warning',
      title: 'Risk Warning',
      message: 'High volatility detected in your portfolio',
      timestamp: new Date(Date.now() - 30 * 60 * 1000),
      read: true,
      icon: AlertTriangle,
      color: 'orange'
    },
    {
      id: 4,
      type: 'market_update',
      title: 'Market Update',
      message: 'NIFTY 50 closed down 0.32% today',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      read: true,
      icon: TrendingDown,
      color: 'red'
    }
  ]);

  const [isOpen, setIsOpen] = useState(false);
  const toast = useToast();

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const unreadCount = notifications.filter(n => !n.read).length;

  // Simulate real-time notifications
  useEffect(() => {
    const interval = setInterval(() => {
      // Randomly add new notifications for demo
      if (Math.random() > 0.8) {
        const newNotification = {
          id: Date.now(),
          type: 'price_alert',
          title: 'New Price Alert',
          message: `Stock ${['RELIANCE', 'TCS', 'INFY'][Math.floor(Math.random() * 3)]} moved significantly`,
          timestamp: new Date(),
          read: false,
          icon: Math.random() > 0.5 ? TrendingUp : TrendingDown,
          color: Math.random() > 0.5 ? 'green' : 'red'
        };

        setNotifications(prev => [newNotification, ...prev.slice(0, 9)]);
        
        if (!isOpen) {
          toast({
            title: newNotification.title,
            description: newNotification.message,
            status: 'info',
            duration: 3000,
            isClosable: true,
            position: 'top-right',
          });
        }
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [isOpen, toast]);

  const markAsRead = (id) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id 
          ? { ...notification, read: true }
          : notification
      )
    );
  };

  const markAllAsRead = () => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    );
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  };

  return (
    <Popover isOpen={isOpen} onClose={() => setIsOpen(false)} placement="bottom-end">
      <PopoverTrigger>
        <Box position="relative">
          <IconButton
            icon={<Bell size={20} />}
            variant="ghost"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Notifications"
            position="relative"
          />
          {unreadCount > 0 && (
            <MotionBox
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              position="absolute"
              top={-1}
              right={-1}
              bg="red.500"
              color="white"
              borderRadius="full"
              minW={5}
              h={5}
              display="flex"
              alignItems="center"
              justifyContent="center"
              fontSize="xs"
              fontWeight="bold"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </MotionBox>
          )}
        </Box>
      </PopoverTrigger>

      <PopoverContent w="400px" bg={cardBg} borderColor={borderColor} boxShadow="xl">
        <PopoverHeader>
          <HStack justify="space-between">
            <Text fontWeight="bold">Notifications</Text>
            <HStack spacing={2}>
              {unreadCount > 0 && (
                <Button size="xs" variant="ghost" onClick={markAllAsRead}>
                  Mark all read
                </Button>
              )}
              <Badge colorScheme="blue" variant="subtle">
                {unreadCount} new
              </Badge>
            </HStack>
          </HStack>
        </PopoverHeader>
        <PopoverCloseButton />

        <PopoverBody p={0} maxH="400px" overflowY="auto">
          <VStack spacing={0} align="stretch">
            <AnimatePresence>
              {notifications.map((notification, index) => {
                const NotificationIcon = notification.icon;
                return (
                  <MotionBox
                    key={notification.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Box
                      p={4}
                      borderBottomWidth="1px"
                      borderColor={borderColor}
                      _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}
                      cursor="pointer"
                      onClick={() => markAsRead(notification.id)}
                      position="relative"
                    >
                      <HStack spacing={3} align="start">
                        <Box
                          p={2}
                          borderRadius="md"
                          bg={`${notification.color}.100`}
                          color={`${notification.color}.600`}
                          flexShrink={0}
                        >
                          <NotificationIcon size={16} />
                        </Box>

                        <VStack spacing={1} align="start" flex={1}>
                          <HStack justify="space-between" w="full">
                            <Text 
                              fontSize="sm" 
                              fontWeight={notification.read ? "normal" : "semibold"}
                              color={notification.read ? "gray.600" : "inherit"}
                            >
                              {notification.title}
                            </Text>
                            <IconButton
                              icon={<X size={14} />}
                              size="xs"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeNotification(notification.id);
                              }}
                              aria-label="Remove notification"
                            />
                          </HStack>
                          
                          <Text 
                            fontSize="xs" 
                            color="gray.500"
                            lineHeight="short"
                          >
                            {notification.message}
                          </Text>
                          
                          <Text fontSize="xs" color="gray.400">
                            {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
                          </Text>
                        </VStack>

                        {!notification.read && (
                          <Box
                            w={2}
                            h={2}
                            bg="blue.500"
                            borderRadius="full"
                            flexShrink={0}
                            mt={1}
                          />
                        )}
                      </HStack>
                    </Box>
                  </MotionBox>
                );
              })}
            </AnimatePresence>

            {notifications.length === 0 && (
              <Box p={8} textAlign="center">
                <Bell size={32} color="gray.400" style={{ margin: '0 auto 16px' }} />
                <Text color="gray.500">No notifications yet</Text>
                <Text fontSize="sm" color="gray.400">
                  You'll see updates about your investments here
                </Text>
              </Box>
            )}
          </VStack>
        </PopoverBody>
      </PopoverContent>
    </Popover>
  );
};

export default NotificationCenter;
