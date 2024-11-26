import React, { useState, useEffect } from 'react';
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

const ExtractStage = ({
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
    const [extractionStats, setExtractionStats] = useState({
        totalEntities: 0,
        entitiesByType: {},
        processingProgress: {
            processed: 0,
            total: 0
        }
    });
    const toast = useToast();

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/extract`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to start extraction');

            const data = await response.json();
            setExtractionStats(data);
            setStatus('completed');
            onComplete();
        } catch (error) {
            console.error('Error during extraction:', error);
            setStatus('failed');
            toast({
                title: 'Error',
                description: 'Failed to complete extraction',
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
            title="Extract Entities"
            description="Identify and extract domain-specific entities"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={6} align="stretch">
                {/* Basic Stats */}
                <Grid templateColumns="repeat(2, 1fr)" gap={4}>
                    <GridItem>
                        <Box p={4} bg="blue.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Total Entities</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {extractionStats.totalEntities}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="green.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Progress</Text>
                            <Progress
                                value={(extractionStats.processingProgress.processed /
                                    extractionStats.processingProgress.total) * 100}
                                size="sm"
                                colorScheme="green"
                            />
                        </Box>
                    </GridItem>
                </Grid>

                {/* Entities Table */}
                <Box>
                    <Text fontWeight="bold" mb={3}>Extracted Entities by Type</Text>
                    <Table variant="simple">
                        <Thead>
                            <Tr>
                                <Th>Type</Th>
                                <Th>Count</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            {Object.entries(extractionStats.entitiesByType).map(([type, count]) => (
                                <Tr key={type}>
                                    <Td>{type}</Td>
                                    <Td>
                                        <Badge colorScheme="blue">{count}</Badge>
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

export default ExtractStage;