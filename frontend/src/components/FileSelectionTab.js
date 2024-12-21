import React, { useState, useEffect } from 'react';
import {
    Box,
    Button,
    VStack,
    Text,
    useToast,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Checkbox,
    Badge,
    Spinner,
    Alert,
    AlertIcon,
} from '@chakra-ui/react';

const FileSelectionTab = ({ version, token, currentTenant, domain_id, onFilesUpdate }) => {
    const [files, setFiles] = useState([]);
    const [selectedFileVersions, setSelectedFileVersions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const toast = useToast();

    useEffect(() => {
        fetchFiles();
    }, [domain_id]);

    const fetchFiles = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/files`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch files');
            const data = await response.json();
            setFiles(data);
        } catch (error) {
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleFileVersionSelect = (fileVersionId) => {
        setSelectedFileVersions(prev => {
            if (prev.includes(fileVersionId)) {
                return prev.filter(id => id !== fileVersionId);
            }
            return [...prev, fileVersionId];
        });
    };

    const addFilesToVersion = async () => {
        setSubmitting(true);
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions/${version.version_number}/files`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_version_ids: selectedFileVersions
                    })
                }
            );

            if (!response.ok) throw new Error('Failed to add files to version');

            toast({
                title: 'Success',
                description: 'Files added to version successfully',
                status: 'success',
                duration: 3000,
            });
            
            onFilesUpdate();
            setSelectedFileVersions([]);
        } catch (error) {
            toast({
                title: 'Error',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <Spinner size="xl" />;
    if (error) return <Alert status="error"><AlertIcon />{error}</Alert>;

    return (
        <VStack spacing={4} align="stretch">
            <Box>
                <Text fontWeight="bold" mb={4}>Available Files</Text>
                <Table variant="simple">
                    <Thead>
                        <Tr>
                            <Th>Select</Th>
                            <Th>File Name</Th>
                            <Th>Version</Th>
                            <Th>Size</Th>
                            <Th>Created At</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {files.map((file) => (
                            file.versions.map((fileVersion) => (
                                <Tr key={fileVersion.file_version_id}>
                                    <Td>
                                        <Checkbox
                                            isChecked={selectedFileVersions.includes(fileVersion.file_version_id)}
                                            onChange={() => handleFileVersionSelect(fileVersion.file_version_id)}
                                        />
                                    </Td>
                                    <Td>{file.filename}</Td>
                                    <Td>{fileVersion.version_number}</Td>
                                    <Td>{(fileVersion.file_size / 1024).toFixed(2)} KB</Td>
                                    <Td>{new Date(fileVersion.created_at).toLocaleString()}</Td>
                                </Tr>
                            ))
                        ))}
                    </Tbody>
                </Table>
            </Box>

            {version?.file_versions?.length > 0 && (
                <Box mt={6}>
                    <Text fontWeight="bold" mb={4}>Current Version Files</Text>
                    <Table variant="simple">
                        <Thead>
                            <Tr>
                                <Th>File ID</Th>
                                <Th>Status</Th>
                                <Th>Created At</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            {version.file_versions.map((file) => (
                                <Tr key={file.file_version_id}>
                                    <Td>{file.file_version_id}</Td>
                                    <Td>
                                        <Badge colorScheme={file.status === 'COMPLETED' ? 'green' : 'yellow'}>
                                            {file.status || 'Pending'}
                                        </Badge>
                                    </Td>
                                    <Td>{new Date(file.created_at).toLocaleString()}</Td>
                                </Tr>
                            ))}
                        </Tbody>
                    </Table>
                </Box>
            )}

            <Button
                colorScheme="blue"
                onClick={addFilesToVersion}
                isLoading={submitting}
                isDisabled={selectedFileVersions.length === 0}
            >
                Add Selected Files to Version
            </Button>
        </VStack>
    );
};

export default FileSelectionTab;