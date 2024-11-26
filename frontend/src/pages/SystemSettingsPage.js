import React, { useState, useContext } from 'react';
import {
    Box,
    Container,
    Heading,
    VStack,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
    FormControl,
    FormLabel,
    Input,
    Select,
    Switch,
    Button,
    useToast,
    Text,
    Divider,
    SimpleGrid,
    NumberInput,
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
} from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const SystemSettingsPage = () => {
    const { token, currentTenant } = useContext(AuthContext);
    const toast = useToast();

    const [processingSettings, setProcessingSettings] = useState({
        maxConcurrentTasks: 5,
        timeoutSeconds: 300,
        retryAttempts: 3,
        defaultLanguage: 'en',
        enableCache: true,
    });

    const [apiSettings, setApiSettings] = useState({
        rateLimit: 100,
        rateLimitWindow: 60,
        maxPayloadSize: 10,
        enableCors: true,
    });

    const [storageSettings, setStorageSettings] = useState({
        storageProvider: 'local',
        bucketName: 'domain-data',
        retentionDays: 30,
        compressionEnabled: true,
    });

    const handleSaveProcessingSettings = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/admin/settings/processing`,
                {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(processingSettings),
                }
            );

            if (!response.ok) throw new Error('Failed to save processing settings');

            toast({
                title: 'Settings saved successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error saving processing settings:', error);
            toast({
                title: 'Error saving settings',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleSaveApiSettings = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/admin/settings/api`,
                {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(apiSettings),
                }
            );

            if (!response.ok) throw new Error('Failed to save API settings');

            toast({
                title: 'API settings saved successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error saving API settings:', error);
            toast({
                title: 'Error saving API settings',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleSaveStorageSettings = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/admin/settings/storage`,
                {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(storageSettings),
                }
            );

            if (!response.ok) throw new Error('Failed to save storage settings');

            toast({
                title: 'Storage settings saved successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error saving storage settings:', error);
            toast({
                title: 'Error saving storage settings',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    return (
        <Box minH="100vh" bg="gray.50" py={8}>
            <Container maxW="container.lg">
                <VStack spacing={8} align="stretch">
                    <Heading size="lg">System Settings</Heading>

                    <Box bg="white" shadow="sm" borderRadius="lg" p={6}>
                        <Tabs>
                            <TabList>
                                <Tab>Processing</Tab>
                                <Tab>API</Tab>
                                <Tab>Storage</Tab>
                            </TabList>

                            <TabPanels>
                                <TabPanel>
                                    <VStack spacing={6} align="stretch">
                                        <Text fontSize="lg" fontWeight="bold">Processing Settings</Text>
                                        <Divider />
                                        <SimpleGrid columns={2} spacing={6}>
                                            <FormControl>
                                                <FormLabel>Max Concurrent Tasks</FormLabel>
                                                <NumberInput
                                                    value={processingSettings.maxConcurrentTasks}
                                                    onChange={(value) =>
                                                        setProcessingSettings({
                                                            ...processingSettings,
                                                            maxConcurrentTasks: parseInt(value),
                                                        })
                                                    }
                                                    min={1}
                                                    max={20}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Timeout (seconds)</FormLabel>
                                                <NumberInput
                                                    value={processingSettings.timeoutSeconds}
                                                    onChange={(value) =>
                                                        setProcessingSettings({
                                                            ...processingSettings,
                                                            timeoutSeconds: parseInt(value),
                                                        })
                                                    }
                                                    min={60}
                                                    max={3600}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Retry Attempts</FormLabel>
                                                <NumberInput
                                                    value={processingSettings.retryAttempts}
                                                    onChange={(value) =>
                                                        setProcessingSettings({
                                                            ...processingSettings,
                                                            retryAttempts: parseInt(value),
                                                        })
                                                    }
                                                    min={0}
                                                    max={10}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Default Language</FormLabel>
                                                <Select
                                                    value={processingSettings.defaultLanguage}
                                                    onChange={(e) =>
                                                        setProcessingSettings({
                                                            ...processingSettings,
                                                            defaultLanguage: e.target.value,
                                                        })
                                                    }
                                                >
                                                    <option value="en">English</option>
                                                    <option value="es">Spanish</option>
                                                    <option value="fr">French</option>
                                                </Select>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Enable Cache</FormLabel>
                                                <Switch
                                                    isChecked={processingSettings.enableCache}
                                                    onChange={(e) =>
                                                        setProcessingSettings({
                                                            ...processingSettings,
                                                            enableCache: e.target.checked,
                                                        })
                                                    }
                                                />
                                            </FormControl>
                                        </SimpleGrid>

                                        <Button
                                            colorScheme="blue"
                                            onClick={handleSaveProcessingSettings}
                                            alignSelf="flex-end"
                                            mt={4}
                                        >
                                            Save Processing Settings
                                        </Button>
                                    </VStack>
                                </TabPanel>

                                <TabPanel>
                                    <VStack spacing={6} align="stretch">
                                        <Text fontSize="lg" fontWeight="bold">API Settings</Text>
                                        <Divider />
                                        <SimpleGrid columns={2} spacing={6}>
                                            <FormControl>
                                                <FormLabel>Rate Limit (requests per window)</FormLabel>
                                                <NumberInput
                                                    value={apiSettings.rateLimit}
                                                    onChange={(value) =>
                                                        setApiSettings({
                                                            ...apiSettings,
                                                            rateLimit: parseInt(value),
                                                        })
                                                    }
                                                    min={10}
                                                    max={1000}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Rate Limit Window (seconds)</FormLabel>
                                                <NumberInput
                                                    value={apiSettings.rateLimitWindow}
                                                    onChange={(value) =>
                                                        setApiSettings({
                                                            ...apiSettings,
                                                            rateLimitWindow: parseInt(value),
                                                        })
                                                    }
                                                    min={30}
                                                    max={3600}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Max Payload Size (MB)</FormLabel>
                                                <NumberInput
                                                    value={apiSettings.maxPayloadSize}
                                                    onChange={(value) =>
                                                        setApiSettings({
                                                            ...apiSettings,
                                                            maxPayloadSize: parseInt(value),
                                                        })
                                                    }
                                                    min={1}
                                                    max={100}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Enable CORS</FormLabel>
                                                <Switch
                                                    isChecked={apiSettings.enableCors}
                                                    onChange={(e) =>
                                                        setApiSettings({
                                                            ...apiSettings,
                                                            enableCors: e.target.checked,
                                                        })
                                                    }
                                                />
                                            </FormControl>
                                        </SimpleGrid>

                                        <Button
                                            colorScheme="blue"
                                            onClick={handleSaveApiSettings}
                                            alignSelf="flex-end"
                                            mt={4}
                                        >
                                            Save API Settings
                                        </Button>
                                    </VStack>
                                </TabPanel>

                                <TabPanel>
                                    <VStack spacing={6} align="stretch">
                                        <Text fontSize="lg" fontWeight="bold">Storage Settings</Text>
                                        <Divider />
                                        <SimpleGrid columns={2} spacing={6}>
                                            <FormControl>
                                                <FormLabel>Storage Provider</FormLabel>
                                                <Select
                                                    value={storageSettings.storageProvider}
                                                    onChange={(e) =>
                                                        setStorageSettings({
                                                            ...storageSettings,
                                                            storageProvider: e.target.value,
                                                        })
                                                    }
                                                >
                                                    <option value="local">Local Storage</option>
                                                    <option value="s3">Amazon S3</option>
                                                    <option value="gcs">Google Cloud Storage</option>
                                                </Select>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Bucket Name</FormLabel>
                                                <Input
                                                    value={storageSettings.bucketName}
                                                    onChange={(e) =>
                                                        setStorageSettings({
                                                            ...storageSettings,
                                                            bucketName: e.target.value,
                                                        })
                                                    }
                                                />
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Retention Days</FormLabel>
                                                <NumberInput
                                                    value={storageSettings.retentionDays}
                                                    onChange={(value) =>
                                                        setStorageSettings({
                                                            ...storageSettings,
                                                            retentionDays: parseInt(value),
                                                        })
                                                    }
                                                    min={1}
                                                    max={365}
                                                >
                                                    <NumberInputField />
                                                    <NumberInputStepper>
                                                        <NumberIncrementStepper />
                                                        <NumberDecrementStepper />
                                                    </NumberInputStepper>
                                                </NumberInput>
                                            </FormControl>

                                            <FormControl>
                                                <FormLabel>Enable Compression</FormLabel>
                                                <Switch
                                                    isChecked={storageSettings.compressionEnabled}
                                                    onChange={(e) =>
                                                        setStorageSettings({
                                                            ...storageSettings,
                                                            compressionEnabled: e.target.checked,
                                                        })
                                                    }
                                                />
                                            </FormControl>
                                        </SimpleGrid>

                                        <Button
                                            colorScheme="blue"
                                            onClick={handleSaveStorageSettings}
                                            alignSelf="flex-end"
                                            mt={4}
                                        >
                                            Save Storage Settings
                                        </Button>
                                    </VStack>
                                </TabPanel>
                            </TabPanels>
                        </Tabs>
                    </Box>
                </VStack>
            </Container>
        </Box>
    );
};

export default SystemSettingsPage;