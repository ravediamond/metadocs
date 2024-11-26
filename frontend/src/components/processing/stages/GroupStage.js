import React, { useState, useEffect } from 'react';
import {
    VStack,
    Text,
    Box,
    Grid,
    GridItem,
    Progress,
    Badge,
    Accordion,
    AccordionItem,
    AccordionButton,
    AccordionPanel,
    AccordionIcon,
    useToast,
} from '@chakra-ui/react';
import BaseStage from './BaseStage';

const GroupStage = ({
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
    const [groupStats, setGroupStats] = useState({
        totalGroups: 0,
        totalEntities: 0,
        groups: []
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
                        stage: 'group',
                        previousPipelineId: pipelineId
                    })
                }
            );

            if (!pipelineResponse.ok) throw new Error('Failed to create pipeline');
            const pipelineData = await pipelineResponse.json();
            onPipelineCreate(pipelineData.pipeline_id);

            // Generate groups
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domainId}/groups/generate`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ pipeline_id: pipelineData.pipeline_id })
                }
            );

            if (!response.ok) throw new Error('Failed to generate groups');

            const data = await response.json();
            setGroupStats(data);
            setStatus('completed');
            onComplete();
        } catch (error) {
            console.error('Error generating groups:', error);
            setStatus('failed');
            toast({
                title: 'Error',
                description: 'Failed to generate groups',
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
            title="Group Concepts"
            description="Organize entities into meaningful groups"
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
                            <Text fontSize="sm" color="gray.600">Total Groups</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {groupStats.totalGroups}
                            </Text>
                        </Box>
                    </GridItem>
                    <GridItem>
                        <Box p={4} bg="green.50" rounded="lg">
                            <Text fontSize="sm" color="gray.600">Total Entities</Text>
                            <Text fontSize="2xl" fontWeight="bold">
                                {groupStats.totalEntities}
                            </Text>
                        </Box>
                    </GridItem>
                </Grid>

                {/* Groups List */}
                {groupStats.groups.length > 0 && (
                    <Box>
                        <Text fontWeight="bold" mb={3}>Generated Groups</Text>
                        <Accordion allowMultiple>
                            {groupStats.groups.map((group, index) => (
                                <AccordionItem key={index}>
                                    <h2>
                                        <AccordionButton>
                                            <Box flex="1" textAlign="left">
                                                <Text fontWeight="medium">{group.name}</Text>
                                            </Box>
                                            <Badge colorScheme="blue" mr={2}>
                                                {group.entities.length} entities
                                            </Badge>
                                            <AccordionIcon />
                                        </AccordionButton>
                                    </h2>
                                    <AccordionPanel>
                                        <VStack align="stretch" spacing={2}>
                                            {group.entities.map((entity, entityIndex) => (
                                                <Box
                                                    key={entityIndex}
                                                    p={2}
                                                    bg="gray.50"
                                                    rounded="md"
                                                >
                                                    <Text>{entity.name}</Text>
                                                    <Badge size="sm" colorScheme="purple">
                                                        {entity.type}
                                                    </Badge>
                                                </Box>
                                            ))}
                                        </VStack>
                                    </AccordionPanel>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    </Box>
                )}
            </VStack>
        </BaseStage>
    );
};

export default GroupStage;