import React, { useState } from 'react';
import {
    VStack,
    Text,
    Box,
    Grid,
    GridItem,
    Button,
    Progress,
    Badge,
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    useToast,
} from '@chakra-ui/react';
import { ChevronDown, Download } from 'lucide-react';
import BaseStage from './BaseStage';

const EXPORT_FORMATS = ['OWL', 'RDF', 'JSON-LD', 'TTL'];

const OntologyStage = ({
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
    const [ontologyStats, setOntologyStats] = useState({
        classes: 0,
        properties: 0,
        individuals: 0,
        axioms: 0,
        metrics: {
            consistency: 0
        }
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
                        stage: 'ontology',
                        previousPipelineId: pipelineId
                    })
                }
            );

            if (!pipelineResponse.ok) throw new Error('Failed to create pipeline');
            const pipelineData = await pipelineResponse.json();
            onPipelineCreate(pipelineData.pipeline_id);

            // Generate ontology
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/ontology/generate`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ pipeline_id: pipelineData.pipeline_id })
                }
            );

            if (!response.ok) throw new Error('Failed to generate ontology');

            const data = await response.json();
            setOntologyStats(data);
            setStatus('completed');
            onComplete();
        } catch (error) {
            console.error('Error generating ontology:', error);
            setStatus('failed');
            toast({
                title: 'Error',
                description: 'Failed to generate ontology',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setProcessing(false);
        }
    };

    const handleExport = async (format) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/ontology/export?format=${format}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    }
                }
            );

            if (!response.ok) throw new Error(`Failed to export ontology as ${format}`);

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ontology.${format.toLowerCase()}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            toast({
                title: 'Export successful',
                description: `Ontology exported as ${format}`,
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error exporting ontology:', error);
            toast({
                title: 'Export failed',
                description: `Failed to export ontology as ${format}`,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    return (
        <BaseStage
            title="Create Ontology"
            description="Generate formal ontology structure"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={6} align="stretch">
                {/* Basic Stats */}
                <Grid templateColumns="repeat(4, 1fr)" gap={4}>
                    <GridItem>
                        <Box p={4} bg="blue.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Classes</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {ontologyStats.classes}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="green.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Properties</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {ontologyStats.properties}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="purple.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Individuals</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {ontologyStats.individuals}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="orange.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Axioms</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {ontologyStats.axioms}
                            </Text>
                        </Box>
                    </GridItem>
                </Grid>

                {/* Consistency Score */}
                <Box>
                    <Text mb={2}>Consistency Score</Text>
                    <Progress
                        value={ontologyStats.metrics.consistency * 100}
                        size="sm"
                        colorScheme="green"
                    />
                </Box>

                {/* Export Options */}
                {status === 'completed' && (
                    <Box>
                        <Menu>
                            <MenuButton as={Button} rightIcon={<ChevronDown />} leftIcon={<Download />}>
                                Export Ontology
                            </MenuButton>
                            <MenuList>
                                {EXPORT_FORMATS.map(format => (
                                    <MenuItem
                                        key={format}
                                        onClick={() => handleExport(format)}
                                    >
                                        Export as {format}
                                    </MenuItem>
                                ))}
                            </MenuList>
                        </Menu>
                    </Box>
                )}
            </VStack>
        </BaseStage>
    );
};

export default OntologyStage;