import React, { useState, useEffect } from 'react';
import {
    VStack,
    Text,
    Box,
    Grid,
    GridItem,
    Button,
    Progress,
    useToast,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
} from '@chakra-ui/react';
import { Download, Eye } from 'lucide-react';
import BaseStage from './BaseStage';

const GraphStage = ({
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
    const [graphStats, setGraphStats] = useState({
        nodes: 0,
        edges: 0,
        clusters: 0
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
                        stage: 'graph',
                        previousPipelineId: pipelineId
                    })
                }
            );

            if (!pipelineResponse.ok) throw new Error('Failed to create pipeline');
            const pipelineData = await pipelineResponse.json();
            onPipelineCreate(pipelineData.pipeline_id);

            // Generate graph
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/graph/generate`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ pipeline_id: pipelineData.pipeline_id })
                }
            );

            if (!response.ok) throw new Error('Failed to generate graph');

            const data = await response.json();
            setGraphStats(data);
            setStatus('completed');
            onComplete();
        } catch (error) {
            console.error('Error generating graph:', error);
            setStatus('failed');
            toast({
                title: 'Error',
                description: 'Failed to generate knowledge graph',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setProcessing(false);
        }
    };

    const handleDownload = async (format = 'json') => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/graph/export?format=${format}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to download graph');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `knowledge-graph.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error downloading graph:', error);
            toast({
                title: 'Error',
                description: 'Failed to download graph',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    return (
        <BaseStage
            title="Knowledge Graph"
            description="Generate the final knowledge graph"
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
                            <Text fontSize="sm" color="gray.600">Nodes</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {graphStats.nodes.toLocaleString()}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="green.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Edges</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {graphStats.edges.toLocaleString()}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="purple.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Clusters</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {graphStats.clusters.toLocaleString()}
                            </Text>
                        </Box>
                    </GridItem>
                </Grid>

                {status === 'completed' && (
                    <>
                        {/* Graph View Area */}
                        <Box
                            height="400px"
                            bg="gray.50"
                            borderRadius="lg"
                            display="flex"
                            alignItems="center"
                            justifyContent="center"
                        >
                            <Text color="gray.500">Graph Visualization Area</Text>
                        </Box>

                        {/* Actions */}
                        <Box display="flex" gap={4}>
                            <Button
                                leftIcon={<Eye size={20} />}
                                onClick={() => {
                                    // Implement view functionality
                                }}
                            >
                                View Graph
                            </Button>
                            <Button
                                leftIcon={<Download size={20} />}
                                onClick={() => handleDownload('json')}
                            >
                                Download Graph
                            </Button>
                        </Box>
                    </>
                )}
            </VStack>
        </BaseStage>
    );
};

export default GraphStage;