import React, { useState, useEffect } from 'react';
import {
    VStack,
    Text,
    List,
    ListItem,
    Flex,
    Icon,
    Progress,
    Grid,
    GridItem,
    Box,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Badge,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon, TimeIcon } from '@chakra-ui/icons';
import BaseStage from './BaseStage';

const ParseStage = ({
    domainId,
    version,
    pipelineId,
    onComplete,
    onPipelineCreate,
    processing,
    setProcessing,
    token,
    currentTenant
}) => {
    const [status, setStatus] = useState('pending');
    const [files, setFiles] = useState([]);
    const [progress, setProgress] = useState({});
    const [stats, setStats] = useState({
        totalFiles: 0,
        processed: 0,
        failed: 0,
        processing: 0
    });

    useEffect(() => {
        fetchFiles();
    }, [domainId, token, currentTenant]);

    const fetchFiles = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domainId}/files`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch files');
            const data = await response.json();
            setFiles(data);
            updateStats(data);
        } catch (error) {
            console.error('Error fetching files:', error);
        }
    };

    const updateStats = (filesList) => {
        const stats = filesList.reduce((acc, file) => {
            acc.totalFiles++;
            if (file.status === 'completed') acc.processed++;
            else if (file.status === 'failed') acc.failed++;
            else if (file.status === 'processing') acc.processing++;
            return acc;
        }, {
            totalFiles: 0,
            processed: 0,
            failed: 0,
            processing: 0
        });
        setStats(stats);
    };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            // Create a new pipeline
            const pipelineResponse = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/pipelines`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        stage: 'parse',
                        files: files.map(f => f.id)
                    })
                }
            );

            if (!pipelineResponse.ok) throw new Error('Failed to create pipeline');
            const pipelineData = await pipelineResponse.json();
            onPipelineCreate(pipelineData.pipeline_id);

            // Start processing files
            for (const file of files) {
                setProgress(prev => ({
                    ...prev,
                    [file.id]: { status: 'processing' }
                }));

                const response = await fetch(
                    `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/files/${file.id}/parse`,
                    {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                    }
                );

                if (!response.ok) throw new Error(`Failed to parse file ${file.id}`);

                setProgress(prev => ({
                    ...prev,
                    [file.id]: { status: 'completed' }
                }));
            }

            setStatus('completed');
            onComplete();
        } catch (error) {
            console.error('Error during parsing:', error);
            setStatus('failed');
        } finally {
            setProcessing(false);
        }
    };

    return (
        <BaseStage
            title="Parse Documents"
            description="Convert documents into processable text format"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={6} align="stretch">
                {/* Statistics Grid */}
                <Grid templateColumns="repeat(4, 1fr)" gap={4}>
                    <GridItem>
                        <Box p={4} bg="gray.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Total Files</Text>
                            <Text fontSize="2xl" fontWeight="bold">{stats.totalFiles}</Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="green.50" rounded="lg">
                            <Text fontSize="sm" color="green.600">Processed</Text>
                            <Text fontSize="2xl" fontWeight="bold" color="green.600">
                                {stats.processed}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="yellow.50" rounded="lg">
                            <Text fontSize="sm" color="yellow.600">Processing</Text>
                            <Text fontSize="2xl" fontWeight="bold" color="yellow.600">
                                {stats.processing}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="red.50" rounded="lg">
                            <Text fontSize="sm" color="red.600">Failed</Text>
                            <Text fontSize="2xl" fontWeight="bold" color="red.600">
                                {stats.failed}
                            </Text>
                        </Box>
                    </GridItem>
                </Grid>

                {/* Progress Bar */}
                <Box>
                    <Text mb={2}>Overall Progress</Text>
                    <Progress
                        value={(stats.processed / stats.totalFiles) * 100}
                        size="sm"
                        colorScheme="blue"
                        rounded="full"
                    />
                </Box>

                {/* Files Table */}
                <Box overflowX="auto">
                    <Table variant="simple">
                        <Thead>
                            <Tr>
                                <Th>File Name</Th>
                                <Th>Size</Th>
                                <Th>Type</Th>
                                <Th>Status</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            {files.map((file) => (
                                <Tr key={file.id}>
                                    <Td>{file.name}</Td>
                                    <Td>{formatFileSize(file.size)}</Td>
                                    <Td>{file.type}</Td>
                                    <Td>
                                        <Badge
                                            colorScheme={
                                                progress[file.id]?.status === 'completed'
                                                    ? 'green'
                                                    : progress[file.id]?.status === 'processing'
                                                        ? 'yellow'
                                                        : 'gray'
                                            }
                                        >
                                            {progress[file.id]?.status || 'pending'}
                                        </Badge>
                                    </Td>
                                </Tr>
                            ))}
                        </Tbody>
                    </Table>
                </Box>
            </VStack>
        </BaseStage>
    );
};

const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export default ParseStage;