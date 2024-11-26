import React, { useState } from 'react';
import {
    VStack,
    Text,
    Box,
    Grid,
    GridItem,
    Progress,
    Badge,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    useToast,
} from '@chakra-ui/react';
import BaseStage from './BaseStage';

const MergeStage = ({
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
    const [mergeStats, setMergeStats] = useState({
        totalEntities: 0,
        mergedEntities: 0,
        duplicatesRemoved: 0,
        mergesByType: []
    });
    const toast = useToast();

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            // Create new pipeline
            const pipelineResponse = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/pipelines`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        stage: 'merge',
                        previousPipelineId: pipelineId
                    })
                }
            );

            if (!pipelineResponse.ok) throw new Error('Failed to create pipeline');
            const pipelineData = await pipelineResponse.json();
            onPipelineCreate(pipelineData.pipeline_id);

            // Start merge process
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/merge`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ pipeline_id: pipelineData.pipeline_id })
                }
            );

            if (!response.ok) throw new Error('Failed to complete merge process');

            const data = await response.json();
            setMergeStats(data);
            setStatus('completed');
            onComplete();
        } catch (error) {
            console.error('Error during merge:', error);
            setStatus('failed');
            toast({
                title: 'Error',
                description: 'Failed to complete merge process',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setProcessing(false);
        }
    };

    return (
        <BaseStage
            title="Merge Entities"
            description="Combine and deduplicate entities"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={6} align="stretch">
                {/* Basic Stats */}
                <Grid templateColumns="repeat(3, 1fr)" gap={4}>
                    <GridItem>
                        <Box p={4} bg="blue.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Total Entities</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {mergeStats.totalEntities}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="green.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Merged Entities</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {mergeStats.mergedEntities}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="red.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Duplicates Removed</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {mergeStats.duplicatesRemoved}
                            </Text>
                        </Box>
                    </GridItem>
                </Grid>

                {/* Progress */}
                {status === 'processing' && (
                    <Box>
                        <Text mb={2}>Merge Progress</Text>
                        <Progress
                            value={(mergeStats.mergedEntities / mergeStats.totalEntities) * 100}
                            size="sm"
                            colorScheme="blue"
                        />
                    </Box>
                )}

                {/* Merge Results Table */}
                {status === 'completed' && mergeStats.mergesByType.length > 0 && (
                    <Box>
                        <Text fontWeight="bold" mb={3}>Merge Results by Type</Text>
                        <Table variant="simple">
                            <Thead>
                                <Tr>
                                    <Th>Entity Type</Th>
                                    <Th>Original Count</Th>
                                    <Th>After Merge</Th>
                                    <Th>Duplicates</Th>
                                </Tr>
                            </Thead>
                            <Tbody>
                                {mergeStats.mergesByType.map((merge, index) => (
                                    <Tr key={index}>
                                        <Td>{merge.type}</Td>
                                        <Td>{merge.originalCount}</Td>
                                        <Td>
                                            <Badge colorScheme="green">
                                                {merge.mergedCount}
                                            </Badge>
                                        </Td>
                                        <Td>
                                            <Badge colorScheme="red">
                                                {merge.duplicates}
                                            </Badge>
                                        </Td>
                                    </Tr>
                                ))}
                            </Tbody>
                        </Table>
                    </Box>
                )}
            </VStack>
        </BaseStage>
    );
};

export default MergeStage;