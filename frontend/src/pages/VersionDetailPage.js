import React, { useState, useEffect, useContext } from 'react';
import {
    Box,
    Container,
    Heading,
    VStack,
    Text,
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
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalCloseButton,
    useDisclosure,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Input,
    HStack,
    Progress,
    IconButton,
    Checkbox
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import FileSelectionTab from '../components/FileSelectionTab';

const VersionDetailPage = () => {
    const { domain_id, version_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const navigate = useNavigate();
    const toast = useToast();
    const { isOpen, onOpen, onClose } = useDisclosure();

    const [version, setVersion] = useState(null);
    const [versions, setVersions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchVersionDetails();
        fetchAllVersions();
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
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const fetchAllVersions = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch versions');
            const data = await response.json();
            setVersions(data);
        } catch (error) {
            console.error('Error fetching versions:', error);
        }
    };

    const createNewVersion = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to create version');
            const data = await response.json();
            toast({
                title: 'Version created.',
                description: `Version ${data.version} created successfully.`,
                status: 'success',
                duration: 5000,
            });
            fetchAllVersions();
            navigate(`/domains/${domain_id}/versions/${data.version}`);
        } catch (error) {
            toast({
                title: 'Error creating version.',
                description: error.message,
                status: 'error',
                duration: 5000,
            });
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

    const getStatusColor = (status) => {
        switch (status) {
            case 'DRAFT': return 'gray';
            case 'TO_BE_VALIDATED': return 'yellow';
            case 'PUBLISHED': return 'green';
            case 'PENDING_SUSPENSION': return 'orange';
            case 'SUSPENDED': return 'red';
            case 'PENDING_DELETE': return 'red';
            case 'DELETED': return 'gray';
            default: return 'gray';
        }
    };

    return (
        <Box minH="100vh" bg="gray.50" py={8}>
            <Container maxW="container.lg">
                <VStack spacing={8} align="stretch">
                    <Flex justify="space-between" align="center">
                        <VStack align="start" spacing={2}>
                            <Heading size="lg">Version Details</Heading>
                            <Text color="gray.600">Version {version?.version}</Text>
                        </VStack>
                        <Flex gap={4}>
                            <Button colorScheme="blue" onClick={onOpen}>
                                View All Versions
                            </Button>
                            <Button colorScheme="green" onClick={createNewVersion}>
                                Create New Version
                            </Button>
                        </Flex>
                    </Flex>

                    <Box bg="white" shadow="sm" borderRadius="lg" p={6}>
                        <Flex justify="space-between" align="center" mb={6}>
                            <Text fontSize="xl" fontWeight="bold">Status</Text>
                            <Badge colorScheme={getStatusColor(version?.status)} p={2} fontSize="md">
                                {version?.status}
                            </Badge>
                        </Flex>

                        <Tabs>
                            <TabList>
                                <Tab>Files</Tab>
                                <Tab>Pipeline Info</Tab>
                                <Tab>Details</Tab>
                            </TabList>

                            <TabPanels>
                            <TabPanel>
                                <FileSelectionTab
                                    version={version}
                                    token={token}
                                    currentTenant={currentTenant}
                                    domain_id={domain_id}
                                    onFilesUpdate={fetchVersionDetails}
                                />
                            </TabPanel>

                                <TabPanel>
                                    <VStack align="stretch" spacing={4}>
                                        <Box>
                                            <Text fontWeight="bold">Pipeline ID</Text>
                                            <Text>{version?.pipeline_id || 'No pipeline assigned'}</Text>
                                        </Box>
                                        <Box>
                                            <Text fontWeight="bold">Created At</Text>
                                            <Text>{new Date(version?.created_at).toLocaleString()}</Text>
                                        </Box>
                                    </VStack>
                                </TabPanel>

                                <TabPanel>
                                    <VStack align="stretch" spacing={4}>
                                        <Box>
                                            <Text fontWeight="bold">Version Number</Text>
                                            <Text>{version?.version}</Text>
                                        </Box>
                                        <Box>
                                            <Text fontWeight="bold">Domain ID</Text>
                                            <Text>{version?.domain_id}</Text>
                                        </Box>
                                    </VStack>
                                </TabPanel>
                            </TabPanels>
                        </Tabs>
                    </Box>
                </VStack>
            </Container>

            <Modal isOpen={isOpen} onClose={onClose} size="xl">
                <ModalOverlay />
                <ModalContent>
                    <ModalHeader>All Versions</ModalHeader>
                    <ModalCloseButton />
                    <ModalBody pb={6}>
                        <Table variant="simple">
                            <Thead>
                                <Tr>
                                    <Th>Version</Th>
                                    <Th>Status</Th>
                                    <Th>Created</Th>
                                    <Th>Action</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                {versions.map((v) => (
                                    <Tr key={v.version}>
                                        <Td>{v.version}</Td>
                                        <Td>
                                            <Badge colorScheme={getStatusColor(v.status)}>
                                                {v.status}
                                            </Badge>
                                        </Td>
                                        <Td>{new Date(v.created_at).toLocaleDateString()}</Td>
                                        <Td>
                                            <Button
                                                size="sm"
                                                onClick={() => {
                                                    navigate(`/domains/${domain_id}/versions/${v.version}`);
                                                    onClose();
                                                }}
                                            >
                                                View
                                            </Button>
                                        </Td>
                                    </Tr>
                                ))}
                            </Tbody>
                        </Table>
                    </ModalBody>
                </ModalContent>
            </Modal>
        </Box>
    );
};

export default VersionDetailPage;