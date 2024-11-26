import React, { useState, useEffect, useContext } from 'react';
import {
    Box,
    Container,
    Heading,
    VStack,
    Text,
    Grid,
    GridItem,
    Badge,
    Button,
    useToast,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
    List,
    ListItem,
    Flex,
    Spinner,
    Alert,
    AlertIcon,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';

const VersionDetailPage = () => {
    const { domain_id, version_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const navigate = useNavigate();
    const toast = useToast();

    const [version, setVersion] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchVersionDetails();
    }, [domain_id, version_id]);

    const fetchVersionDetails = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions/${version_id}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to fetch version details');
            const data = await response.json();
            setVersion(data);
        } catch (error) {
            console.error('Error fetching version details:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Flex justify="center" align="center" minH="100vh">
                <Spinner size="xl" />
            </Flex>
        );
    }

    if (error) {
        return (
            <Container maxW="container.lg" py={8}>
                <Alert status="error">
                    <AlertIcon />
                    {error}
                </Alert>
            </Container>
        );
    }

    return (
        <Box minH="100vh" bg="gray.50" py={8}>
            <Container maxW="container.lg">
                <VStack spacing={8} align="stretch">
                    <Flex justify="space-between" align="center">
                        <VStack align="start" spacing={2}>
                            <Heading size="lg">Version Details</Heading>
                            <Text color="gray.600">Version {version?.version_number}</Text>
                        </VStack>
                        <Badge
                            colorScheme={
                                version?.status === 'validated'
                                    ? 'green'
                                    : version?.status === 'processing'
                                        ? 'blue'
                                        : 'yellow'
                            }
                            p={2}
                            fontSize="md"
                        >
                            {version?.status}
                        </Badge>
                    </Flex>

                    <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                        <StatsCard
                            title="Files"
                            value={version?.file_count}
                            label="Total Files"
                        />
                        <StatsCard
                            title="Entities"
                            value={version?.entity_count}
                            label="Extracted Entities"
                        />
                        <StatsCard
                            title="Relations"
                            value={version?.relation_count}
                            label="Identified Relations"
                        />
                    </Grid>

                    <Box bg="white" shadow="sm" borderRadius="lg" p={6}>
                        <Tabs>
                            <TabList>
                                <Tab>Files</Tab>
                                <Tab>Processing History</Tab>
                                <Tab>Validation Results</Tab>
                            </TabList>

                            <TabPanels>
                                <TabPanel>
                                    <List spacing={3}>
                                        {version?.files.map((file) => (
                                            <ListItem key={file.file_id}>
                                                <Flex justify="space-between" align="center">
                                                    <Text>{file.filename}</Text>
                                                    <Badge colorScheme={file.processed ? 'green' : 'yellow'}>
                                                        {file.processed ? 'Processed' : 'Pending'}
                                                    </Badge>
                                                </Flex>
                                            </ListItem>
                                        ))}
                                    </List>
                                </TabPanel>

                                <TabPanel>
                                    <List spacing={3}>
                                        {version?.processing_history.map((event, index) => (
                                            <ListItem key={index}>
                                                <Text fontWeight="bold">{event.stage}</Text>
                                                <Text fontSize="sm" color="gray.600">
                                                    {new Date(event.timestamp).toLocaleString()}
                                                </Text>
                                                <Badge colorScheme={event.status === 'completed' ? 'green' : 'yellow'}>
                                                    {event.status}
                                                </Badge>
                                            </ListItem>
                                        ))}
                                    </List>
                                </TabPanel>

                                <TabPanel>
                                    {version?.validation_results ? (
                                        <VStack align="stretch" spacing={4}>
                                            {version.validation_results.checks.map((check, index) => (
                                                <Box
                                                    key={index}
                                                    p={4}
                                                    borderRadius="md"
                                                    bg="gray.50"
                                                    border="1px"
                                                    borderColor="gray.200"
                                                >
                                                    <Flex justify="space-between" align="center">
                                                        <Text fontWeight="bold">{check.name}</Text>
                                                        <Badge colorScheme={check.passed ? 'green' : 'red'}>
                                                            {check.passed ? 'Passed' : 'Failed'}
                                                        </Badge>
                                                    </Flex>
                                                    {!check.passed && (
                                                        <Text color="red.500" fontSize="sm" mt={2}>
                                                            {check.message}
                                                        </Text>
                                                    )}
                                                </Box>
                                            ))}
                                        </VStack>
                                    ) : (
                                        <Text>No validation results available</Text>
                                    )}
                                </TabPanel>
                            </TabPanels>
                        </Tabs>
                    </Box>
                </VStack>
            </Container>
        </Box>
    );
};

const StatsCard = ({ title, value, label }) => (
    <Box bg="white" p={6} borderRadius="lg" shadow="sm">
        <Text fontSize="sm" color="gray.500">
            {title}
        </Text>
        <Text fontSize="3xl" fontWeight="bold" my={2}>
            {value}
        </Text>
        <Text fontSize="sm" color="gray.600">
            {label}
        </Text>
    </Box>
);

export default VersionDetailPage;