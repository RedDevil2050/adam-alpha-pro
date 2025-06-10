import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Text,
  HStack,
  Alert,
  AlertIcon,
  InputGroup,
  InputRightElement,
  IconButton,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';
import { Eye, EyeOff, Lock, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

const LoginPage = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const inputBg = useColorModeValue('gray.50', 'gray.700');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    const result = await login(formData);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setIsLoading(false);
  };

  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <VStack spacing={8}>
        <VStack spacing={2}>
          <Text fontSize="2xl" fontWeight="bold">
            Welcome Back
          </Text>
          <Text color="gray.500" textAlign="center">
            Sign in to access your market analysis dashboard
          </Text>
        </VStack>

        {error && (
          <Alert status="error" borderRadius="lg">
            <AlertIcon />
            {error}
          </Alert>
        )}

        <Box w="full">
          <form onSubmit={handleSubmit}>
            <VStack spacing={6}>
              <FormControl isRequired>
                <FormLabel>Username</FormLabel>
                <InputGroup>
                  <Input
                    name="username"
                    type="text"
                    value={formData.username}
                    onChange={handleChange}
                    placeholder="Enter your username"
                    bg={inputBg}
                    border="1px"
                    borderColor={useColorModeValue('gray.300', 'gray.600')}
                    _hover={{
                      borderColor: 'brand.400',
                    }}
                    _focus={{
                      borderColor: 'brand.500',
                      boxShadow: '0 0 0 1px var(--chakra-colors-brand-500)',
                    }}
                    pl={10}
                  />
                  <InputRightElement pointerEvents="none">
                    <User size={18} color="gray.400" />
                  </InputRightElement>
                </InputGroup>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Password</FormLabel>
                <InputGroup>
                  <Input
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Enter your password"
                    bg={inputBg}
                    border="1px"
                    borderColor={useColorModeValue('gray.300', 'gray.600')}
                    _hover={{
                      borderColor: 'brand.400',
                    }}
                    _focus={{
                      borderColor: 'brand.500',
                      boxShadow: '0 0 0 1px var(--chakra-colors-brand-500)',
                    }}
                    pl={10}
                  />
                  <InputRightElement>
                    <IconButton
                      h="1.75rem"
                      size="sm"
                      onClick={() => setShowPassword(!showPassword)}
                      variant="ghost"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      icon={showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    />
                  </InputRightElement>
                </InputGroup>
              </FormControl>

              <Button
                type="submit"
                colorScheme="brand"
                size="lg"
                w="full"
                isLoading={isLoading}
                loadingText="Signing in..."
                leftIcon={<Lock size={18} />}
                _hover={{
                  transform: 'translateY(-1px)',
                  boxShadow: 'lg',
                }}
                transition="all 0.2s"
              >
                Sign In
              </Button>
            </VStack>
          </form>
        </Box>

        <Box w="full">
          <Divider mb={4} />
          <VStack spacing={3}>
            <Text fontSize="sm" color="gray.500" textAlign="center">
              Demo Credentials for Testing
            </Text>
            <HStack spacing={4} fontSize="xs" color="gray.400">
              <Text>Username: <strong>admin</strong></Text>
              <Text>•</Text>
              <Text>Password: <strong>changeme</strong></Text>
            </HStack>
          </VStack>
        </Box>
      </VStack>
    </MotionBox>
  );
};

export default LoginPage;
