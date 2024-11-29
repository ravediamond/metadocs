import React, { useState, useEffect, useContext } from 'react';
import {
    Box,
    Container,
    Heading,
    VStack,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Button,
    Badge,
    Flex,
    useToast,
    Spinner,
    Alert,
    AlertIcon,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';

const DomainVersionsPage = () => {
    const { domain_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const navigate = useNavigate();
    const toast = useToast();

    const [versions, setVersions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchVersions();
    }, [domain_id]);

    const fetchVersions = async () => {
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
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateVersion = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains./tenants/${currentTenant}/domains/${domain_id}/versions`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to create version');

            const newVersion = await response.json();
            setVersions([...versions, newVersion]);

            toast({
                title: 'Version created successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error creating version:', error);
            toast({
                title: 'Error creating version',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleValidateVersion = async (versionId) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions/${versionId}/validate`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to validate version');

            await fetchVersions(); // Refresh the versions list

            toast({
                title: 'Version validated successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error validating version:', error);
            toast({
                title: 'Error validating version',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
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

    return (
        <Box minH="100vh" bg="gray.50" py={8}>
            <Container maxW="container.lg">
                <VStack spacing={8} align="stretch">
                    <Flex justify="space-between" align="center">
                        <Heading size="lg">Domain Versions</Heading>
                        <Button colorScheme="blue" onClick={handleCreateVersion}>
                            Create New Version
                        </Button>
                    </Flex>

                    <Box bg="white" shadow="sm" borderRadius="lg" overflow="hidden">
                        <Table variant="simple">
                            <Thead>
                                <Tr>
                                    <Th>Version</Th>
                                    <Th>Created At</Th>
                                    <Th>Status</Th>
                                    <Th>Files</Th>
                                    <Th>Actions</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                {versions.map((version) => (
                                    <Tr key={version.version_id}>
                                        <Td>v{version.version_number}</Td>
                                        <Td>{new Date(version.created_at).toLocaleString()}</Td>
                                        <Td>
                                            <Badge
                                                colorScheme={
                                                    version.status === 'validated'
                                                        ? 'green'
                                                        : version.status === 'processing'
                                                            ? 'blue'
                                                            : 'yellow'
                                                }
                                            >
                                                {version.status}
                                            </Badge>
                                        </Td>
                                        <Td>{version.file_count} files</Td>
                                        <Td>
                                            <Button
                                                size="sm"
                                                mr={2}
                                                onClick={() => navigate(`/domains/${domain_id}/versions/${version.version_id}`)}
                                            >
                                                View
                                            </Button>
                                            {version.status !== 'validated' && (
                                                <Button
                                                    size="sm"
                                                    colorScheme="green"
                                                    onClick={() => handleValidateVersion(version.version_id)}
                                                >
                                                    Validate
                                                </Button>
                                            )}
                                        </Td>
                                    </Tr>
                                ))}
                            </Tbody>
                        </Table>
                    </Box>
                </VStack>
            </Container>
        </Box>
    );
};

export default DomainVersionsPage;