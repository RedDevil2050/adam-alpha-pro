import React, { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Card,
  CardHeader,
  CardBody,
  Text,
  Button,
  Switch,
  Select,
  Input,
  FormControl,
  FormLabel,
  FormHelperText,
  Divider,
  useColorModeValue,
  useColorMode,
  useToast,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Alert,
  AlertIcon,
  AlertDescription,
  Badge,
  SimpleGrid,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { 
  FiSave, 
  FiRefreshCw, 
  FiBell, 
  FiMoon, 
  FiSun,
  FiShield,
  FiDatabase,
  FiSettings as FiSettingsIcon
} from 'react-icons/fi';

const MotionBox = motion(Box);

const SettingsPage = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();
  
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  // Settings state
  const [settings, setSettings] = useState({
    // General
    defaultCurrency: 'USD',
    refreshInterval: 30,
    enableNotifications: true,
    enableSounds: false,
    
    // Analysis
    defaultTimeframe: '1d',
    riskTolerance: 50,
    enableAutoAnalysis: true,
    analysisDepth: 'standard',
    
    // Alerts
    priceAlerts: true,
    volumeAlerts: false,
    newsAlerts: true,
    technicalAlerts: true,
    
    // API
    apiTimeout: 30,
    rateLimitBuffer: 10,
    enableCaching: true,
    cacheExpiry: 300,
    
    // Security
    sessionTimeout: 60,
    requireMFA: false,
    enableLogging: true,
  });

  const handleSave = async () => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      toast({
        title: 'Settings saved',
        description: 'Your preferences have been updated successfully.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    }, 1000);
  };

  const handleReset = () => {
    setSettings({
      defaultCurrency: 'USD',
      refreshInterval: 30,
      enableNotifications: true,
      enableSounds: false,
      defaultTimeframe: '1d',
      riskTolerance: 50,
      enableAutoAnalysis: true,
      analysisDepth: 'standard',
      priceAlerts: true,
      volumeAlerts: false,
      newsAlerts: true,
      technicalAlerts: true,
      apiTimeout: 30,
      rateLimitBuffer: 10,
      enableCaching: true,
      cacheExpiry: 300,
      sessionTimeout: 60,
      requireMFA: false,
      enableLogging: true,
    });
    toast({
      title: 'Settings reset',
      description: 'All settings have been restored to default values.',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  return (
    <Box bg={bgColor} minH="100vh" py={8}>
      <Container maxW="4xl">
        <MotionBox
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <VStack align="start" spacing={2} mb={8}>
            <Heading size="xl">Settings</Heading>
            <Text color="gray.500">Customize your trading analysis experience</Text>
          </VStack>

          {/* Action Buttons */}
          <HStack spacing={4} mb={8}>
            <Button
              leftIcon={<FiSave />}
              colorScheme="blue"
              onClick={handleSave}
              isLoading={isLoading}
              loadingText="Saving..."
            >
              Save Changes
            </Button>
            <Button
              leftIcon={<FiRefreshCw />}
              variant="outline"
              onClick={handleReset}
            >
              Reset to Defaults
            </Button>
          </HStack>

          {/* Settings Tabs */}
          <Tabs variant="enclosed" colorScheme="blue">
            <TabList>
              <Tab>General</Tab>
              <Tab>Analysis</Tab>
              <Tab>Alerts</Tab>
              <Tab>API & Performance</Tab>
              <Tab>Security</Tab>
            </TabList>

            <TabPanels>
              {/* General Settings */}
              <TabPanel p={0} pt={6}>
                <VStack spacing={6} align="stretch">
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">General Preferences</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={6} align="stretch">
                        <FormControl>
                          <FormLabel>Default Currency</FormLabel>
                          <Select
                            value={settings.defaultCurrency}
                            onChange={(e) => updateSetting('defaultCurrency', e.target.value)}
                          >
                            <option value="USD">USD - US Dollar</option>
                            <option value="EUR">EUR - Euro</option>
                            <option value="GBP">GBP - British Pound</option>
                            <option value="JPY">JPY - Japanese Yen</option>
                          </Select>
                          <FormHelperText>Currency used for all price displays</FormHelperText>
                        </FormControl>

                        <FormControl>
                          <FormLabel>Data Refresh Interval</FormLabel>
                          <HStack>
                            <Slider
                              value={settings.refreshInterval}
                              onChange={(value) => updateSetting('refreshInterval', value)}
                              min={5}
                              max={300}
                              step={5}
                              flex={1}
                            >
                              <SliderTrack>
                                <SliderFilledTrack />
                              </SliderTrack>
                              <SliderThumb />
                            </Slider>
                            <Text minW="60px">{settings.refreshInterval}s</Text>
                          </HStack>
                          <FormHelperText>How often to refresh market data</FormHelperText>
                        </FormControl>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Theme</Text>
                            <Text fontSize="sm" color="gray.500">
                              Switch between light and dark mode
                            </Text>
                          </Box>
                          <HStack>
                            <FiSun />
                            <Switch
                              isChecked={colorMode === 'dark'}
                              onChange={toggleColorMode}
                              colorScheme="blue"
                            />
                            <FiMoon />
                          </HStack>
                        </HStack>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Notifications</Text>
                            <Text fontSize="sm" color="gray.500">
                              Enable desktop notifications
                            </Text>
                          </Box>
                          <Switch
                            isChecked={settings.enableNotifications}
                            onChange={(e) => updateSetting('enableNotifications', e.target.checked)}
                            colorScheme="blue"
                          />
                        </HStack>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Sound Effects</Text>
                            <Text fontSize="sm" color="gray.500">
                              Play sounds for alerts and notifications
                            </Text>
                          </Box>
                          <Switch
                            isChecked={settings.enableSounds}
                            onChange={(e) => updateSetting('enableSounds', e.target.checked)}
                            colorScheme="blue"
                          />
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>
                </VStack>
              </TabPanel>

              {/* Analysis Settings */}
              <TabPanel p={0} pt={6}>
                <VStack spacing={6} align="stretch">
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">Analysis Configuration</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={6} align="stretch">
                        <FormControl>
                          <FormLabel>Default Timeframe</FormLabel>
                          <Select
                            value={settings.defaultTimeframe}
                            onChange={(e) => updateSetting('defaultTimeframe', e.target.value)}
                          >
                            <option value="1m">1 Minute</option>
                            <option value="5m">5 Minutes</option>
                            <option value="15m">15 Minutes</option>
                            <option value="1h">1 Hour</option>
                            <option value="4h">4 Hours</option>
                            <option value="1d">1 Day</option>
                            <option value="1w">1 Week</option>
                          </Select>
                          <FormHelperText>Default chart timeframe for analysis</FormHelperText>
                        </FormControl>

                        <FormControl>
                          <FormLabel>Risk Tolerance</FormLabel>
                          <HStack>
                            <Text fontSize="sm">Conservative</Text>
                            <Slider
                              value={settings.riskTolerance}
                              onChange={(value) => updateSetting('riskTolerance', value)}
                              min={0}
                              max={100}
                              flex={1}
                              colorScheme="orange"
                            >
                              <SliderTrack>
                                <SliderFilledTrack />
                              </SliderTrack>
                              <SliderThumb />
                            </Slider>
                            <Text fontSize="sm">Aggressive</Text>
                          </HStack>
                          <FormHelperText>Affects risk assessment calculations</FormHelperText>
                        </FormControl>

                        <FormControl>
                          <FormLabel>Analysis Depth</FormLabel>
                          <Select
                            value={settings.analysisDepth}
                            onChange={(e) => updateSetting('analysisDepth', e.target.value)}
                          >
                            <option value="basic">Basic - Quick overview</option>
                            <option value="standard">Standard - Comprehensive analysis</option>
                            <option value="advanced">Advanced - Deep dive with all indicators</option>
                          </Select>
                          <FormHelperText>Determines how detailed the analysis will be</FormHelperText>
                        </FormControl>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Auto-Analysis</Text>
                            <Text fontSize="sm" color="gray.500">
                              Automatically run analysis on watchlist symbols
                            </Text>
                          </Box>
                          <Switch
                            isChecked={settings.enableAutoAnalysis}
                            onChange={(e) => updateSetting('enableAutoAnalysis', e.target.checked)}
                            colorScheme="blue"
                          />
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  {settings.enableAutoAnalysis && (
                    <Alert status="info" borderRadius="md">
                      <AlertIcon />
                      <AlertDescription>
                        Auto-analysis will run every {settings.refreshInterval} seconds for symbols in your watchlist.
                        This may consume more API credits.
                      </AlertDescription>
                    </Alert>
                  )}
                </VStack>
              </TabPanel>

              {/* Alerts Settings */}
              <TabPanel p={0} pt={6}>
                <VStack spacing={6} align="stretch">
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">Alert Preferences</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={6} align="stretch">
                        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                          <HStack justify="space-between">
                            <Box>
                              <Text fontWeight="semibold">Price Alerts</Text>
                              <Text fontSize="sm" color="gray.500">
                                Notify on significant price movements
                              </Text>
                            </Box>
                            <Switch
                              isChecked={settings.priceAlerts}
                              onChange={(e) => updateSetting('priceAlerts', e.target.checked)}
                              colorScheme="green"
                            />
                          </HStack>

                          <HStack justify="space-between">
                            <Box>
                              <Text fontWeight="semibold">Volume Alerts</Text>
                              <Text fontSize="sm" color="gray.500">
                                Alert on unusual volume spikes
                              </Text>
                            </Box>
                            <Switch
                              isChecked={settings.volumeAlerts}
                              onChange={(e) => updateSetting('volumeAlerts', e.target.checked)}
                              colorScheme="blue"
                            />
                          </HStack>

                          <HStack justify="space-between">
                            <Box>
                              <Text fontWeight="semibold">News Alerts</Text>
                              <Text fontSize="sm" color="gray.500">
                                Breaking news and earnings updates
                              </Text>
                            </Box>
                            <Switch
                              isChecked={settings.newsAlerts}
                              onChange={(e) => updateSetting('newsAlerts', e.target.checked)}
                              colorScheme="orange"
                            />
                          </HStack>

                          <HStack justify="space-between">
                            <Box>
                              <Text fontWeight="semibold">Technical Alerts</Text>
                              <Text fontSize="sm" color="gray.500">
                                Technical indicator signals
                              </Text>
                            </Box>
                            <Switch
                              isChecked={settings.technicalAlerts}
                              onChange={(e) => updateSetting('technicalAlerts', e.target.checked)}
                              colorScheme="purple"
                            />
                          </HStack>
                        </SimpleGrid>
                      </VStack>
                    </CardBody>
                  </Card>
                </VStack>
              </TabPanel>

              {/* API & Performance Settings */}
              <TabPanel p={0} pt={6}>
                <VStack spacing={6} align="stretch">
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">API Configuration</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={6} align="stretch">
                        <FormControl>
                          <FormLabel>API Timeout (seconds)</FormLabel>
                          <NumberInput
                            value={settings.apiTimeout}
                            onChange={(value) => updateSetting('apiTimeout', parseInt(value))}
                            min={5}
                            max={120}
                          >
                            <NumberInputField />
                            <NumberInputStepper>
                              <NumberIncrementStepper />
                              <NumberDecrementStepper />
                            </NumberInputStepper>
                          </NumberInput>
                          <FormHelperText>Maximum time to wait for API responses</FormHelperText>
                        </FormControl>

                        <FormControl>
                          <FormLabel>Rate Limit Buffer (%)</FormLabel>
                          <Slider
                            value={settings.rateLimitBuffer}
                            onChange={(value) => updateSetting('rateLimitBuffer', value)}
                            min={0}
                            max={50}
                          >
                            <SliderTrack>
                              <SliderFilledTrack />
                            </SliderTrack>
                            <SliderThumb />
                          </Slider>
                          <FormHelperText>Safety buffer for API rate limits: {settings.rateLimitBuffer}%</FormHelperText>
                        </FormControl>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Enable Caching</Text>
                            <Text fontSize="sm" color="gray.500">
                              Cache API responses to improve performance
                            </Text>
                          </Box>
                          <Switch
                            isChecked={settings.enableCaching}
                            onChange={(e) => updateSetting('enableCaching', e.target.checked)}
                            colorScheme="blue"
                          />
                        </HStack>

                        {settings.enableCaching && (
                          <FormControl>
                            <FormLabel>Cache Expiry (seconds)</FormLabel>
                            <NumberInput
                              value={settings.cacheExpiry}
                              onChange={(value) => updateSetting('cacheExpiry', parseInt(value))}
                              min={60}
                              max={3600}
                            >
                              <NumberInputField />
                              <NumberInputStepper>
                                <NumberIncrementStepper />
                                <NumberDecrementStepper />
                              </NumberInputStepper>
                            </NumberInput>
                            <FormHelperText>How long to keep cached data</FormHelperText>
                          </FormControl>
                        )}
                      </VStack>
                    </CardBody>
                  </Card>
                </VStack>
              </TabPanel>

              {/* Security Settings */}
              <TabPanel p={0} pt={6}>
                <VStack spacing={6} align="stretch">
                  <Card bg={cardBg}>
                    <CardHeader>
                      <Heading size="md">Security & Privacy</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={6} align="stretch">
                        <FormControl>
                          <FormLabel>Session Timeout (minutes)</FormLabel>
                          <Select
                            value={settings.sessionTimeout}
                            onChange={(e) => updateSetting('sessionTimeout', parseInt(e.target.value))}
                          >
                            <option value={15}>15 minutes</option>
                            <option value={30}>30 minutes</option>
                            <option value={60}>1 hour</option>
                            <option value={120}>2 hours</option>
                            <option value={480}>8 hours</option>
                          </Select>
                          <FormHelperText>Automatically log out after inactivity</FormHelperText>
                        </FormControl>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Multi-Factor Authentication</Text>
                            <Text fontSize="sm" color="gray.500">
                              Require additional verification for login
                            </Text>
                          </Box>
                          <HStack>
                            <Switch
                              isChecked={settings.requireMFA}
                              onChange={(e) => updateSetting('requireMFA', e.target.checked)}
                              colorScheme="red"
                            />
                            <Badge colorScheme="orange">Recommended</Badge>
                          </HStack>
                        </HStack>

                        <HStack justify="space-between">
                          <Box>
                            <Text fontWeight="semibold">Activity Logging</Text>
                            <Text fontSize="sm" color="gray.500">
                              Log user actions for security audit
                            </Text>
                          </Box>
                          <Switch
                            isChecked={settings.enableLogging}
                            onChange={(e) => updateSetting('enableLogging', e.target.checked)}
                            colorScheme="blue"
                          />
                        </HStack>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Alert status="warning" borderRadius="md">
                    <AlertIcon />
                    <AlertDescription>
                      Security settings changes will take effect on your next login session.
                    </AlertDescription>
                  </Alert>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </MotionBox>
      </Container>
    </Box>
  );
};

export default SettingsPage;
