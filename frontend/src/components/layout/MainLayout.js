import React, { useState } from 'react';
import {
  Box,
  Flex,
  HStack,
  VStack,
  Text,
  Button,
  Avatar,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  useColorMode,
  useColorModeValue,
  IconButton,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  useDisclosure,
  Badge,
  Container,
} from '@chakra-ui/react';
import { 
  BarChart3, 
  TrendingUp, 
  Briefcase, 
  Star, 
  Settings, 
  Moon, 
  Sun, 
  Menu as MenuIcon,
  LogOut,
  User,
  Home
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { motion } from 'framer-motion';
// Import new components
import APIConnectionStatus from '../common/APIConnectionStatus';
import NotificationCenter from '../common/NotificationCenter';

const MotionBox = motion(Box);

const MainLayout = ({ children }) => {
  const { colorMode, toggleColorMode } = useColorMode();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const navigationItems = [
    { name: 'Dashboard', path: '/dashboard', icon: Home },
    { name: 'Analysis', path: '/analysis', icon: BarChart3 },
    { name: 'Screener', path: '/screener', icon: TrendingUp },
    { name: 'Portfolio', path: '/portfolio', icon: Briefcase },
    { name: 'Watchlist', path: '/watchlist', icon: Star },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  const handleNavigation = (path) => {
    navigate(path);
    onClose();
  };

  const NavItem = ({ item, isMobile = false }) => {
    const isActive = location.pathname === item.path;
    const Icon = item.icon;

    return (
      <MotionBox
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <Button
          variant={isActive ? 'solid' : 'ghost'}
          colorScheme={isActive ? 'brand' : 'gray'}
          justifyContent={isMobile ? 'flex-start' : 'center'}
          leftIcon={<Icon size={20} />}
          w={isMobile ? 'full' : 'auto'}
          onClick={() => handleNavigation(item.path)}
          size="md"
          px={isMobile ? 6 : 4}
          _hover={{
            transform: 'translateY(-1px)',
            boxShadow: 'md'
          }}
          transition="all 0.2s"
        >
          {isMobile && item.name}
        </Button>
      </MotionBox>
    );
  };

  return (
    <Flex h="100vh" direction="column">
      {/* Top Navigation Bar */}
      <Box
        bg={bg}
        borderBottom="1px"
        borderColor={borderColor}
        px={6}
        py={4}
        position="sticky"
        top={0}
        zIndex={1000}
        boxShadow="sm"
      >
        <Flex justify="space-between" align="center">
          {/* Left Side - Logo & Navigation */}
          <Flex align="center" gap={8}>
            <MotionBox
              whileHover={{ scale: 1.05 }}
              cursor="pointer"
              onClick={() => navigate('/dashboard')}
            >
              <HStack>
                <Box
                  bg="brand.500"
                  p={2}
                  borderRadius="lg"
                  color="white"
                >
                  <TrendingUp size={24} />
                </Box>
                <VStack align="start" spacing={0}>
                  <Text fontWeight="bold" fontSize="lg">
                    Zion
                  </Text>
                  <Text fontSize="xs" color={textColor}>
                    Market Analysis
                  </Text>
                </VStack>
              </HStack>
            </MotionBox>

            {/* Desktop Navigation */}
            <HStack spacing={2} display={{ base: 'none', md: 'flex' }}>
              {navigationItems.map((item) => (
                <NavItem key={item.path} item={item} />
              ))}
            </HStack>
          </Flex>

          {/* Right Side - API Status, Notifications, User Menu & Settings */}
          <HStack spacing={4}>
            {/* API Connection Status */}
            <Box display={{ base: 'none', md: 'block' }}>
              <APIConnectionStatus />
            </Box>

            {/* Notifications */}
            <NotificationCenter />

            <IconButton
              icon={colorMode === 'light' ? <Moon size={20} /> : <Sun size={20} />}
              onClick={toggleColorMode}
              variant="ghost"
              aria-label="Toggle color mode"
              _hover={{ bg: useColorModeValue('gray.100', 'gray.700') }}
            />

            {/* Mobile Menu Button */}
            <IconButton
              icon={<MenuIcon size={20} />}
              onClick={onOpen}
              variant="ghost"
              display={{ base: 'flex', md: 'none' }}
              aria-label="Open navigation menu"
            />

            {/* User Menu */}
            <Menu>
              <MenuButton as={Button} variant="ghost" p={1}>
                <HStack>
                  <Avatar size="sm" name={user?.username || 'User'} />
                  <VStack align="start" spacing={0} display={{ base: 'none', md: 'flex' }}>
                    <Text fontSize="sm" fontWeight="medium">
                      {user?.username || 'User'}
                    </Text>
                    <Badge colorScheme="green" fontSize="xs">
                      Active
                    </Badge>
                  </VStack>
                </HStack>
              </MenuButton>
              <MenuList>
                <MenuItem icon={<User size={16} />}>
                  Profile
                </MenuItem>
                <MenuItem icon={<Settings size={16} />} onClick={() => navigate('/settings')}>
                  Settings
                </MenuItem>
                <MenuDivider />
                <MenuItem icon={<LogOut size={16} />} onClick={logout}>
                  Logout
                </MenuItem>
              </MenuList>
            </Menu>
          </HStack>
        </Flex>
      </Box>

      {/* Mobile Navigation Drawer */}
      <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerHeader borderBottomWidth="1px">
            <HStack>
              <Box bg="brand.500" p={2} borderRadius="lg" color="white">
                <TrendingUp size={20} />
              </Box>
              <Text>Navigation</Text>
            </HStack>
          </DrawerHeader>
          <DrawerBody>
            <VStack spacing={2} align="stretch" pt={4}>
              {navigationItems.map((item) => (
                <NavItem key={item.path} item={item} isMobile />
              ))}
              
              {/* Mobile API Status */}
              <Box pt={4}>
                <APIConnectionStatus />
              </Box>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Main Content */}
      <Box flex={1} overflow="auto">
        <Container maxW="container.xl" py={6}>
          {children}
        </Container>
      </Box>
    </Flex>
  );
};

export default MainLayout;
