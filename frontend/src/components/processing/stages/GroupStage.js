import React, { useState, useEffect } from 'react';
import {
    VStack,
    Text,
    List,
    ListItem,
    Flex,
    Icon,
    Box,
    Badge,
    SimpleGrid,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import BaseStage from './BaseStage';

const GroupStage = ({
    domainId,
    version,
    pipelineId,
    onComplete,
    onPipelineCreate,
    processing,
    setProcessing,
}) => {
    const [status, setStatus] = useState('pending');
    const [mergedEntities, setMergedEntities] = useState([]);
    const [groups, setGroups] = useState([]);

    useEffect(() => {
        fetchMergedEntities();
    }, [domainId]);

    const fetchMergedEntities = async () => {
        try {
            const response = await fetch(`/api/domains/${domainId}/merged-entities`);
            const data = await response.json();
            setMergedEntities(data);
        } catch (error) {
            console.error('Error fetching merged entities:', error);
        }
    };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            const response = await fetch(
                `/api/domains/${domainId}/group`,
                {
                    method: 'POST',
                }
            );
            const data = await response.json();

            // Simulate groups
            setGroups([
                { name: 'Products', entityCount: 45, confidence: 0.9 },
                { name: 'Processes', entityCount: 30, confidence: 0.85 },
                { name: 'Stakeholders', entityCount: 25, confidence: 0.95 },
                { name: 'Resources', entityCount: 20, confidence: 0.88 },
            ]);

            setStatus('completed');
            onComplete();
        } catch (error) {
            setStatus('failed');
            console.error('Error during grouping:', error);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <BaseStage
            title="Group Concepts"
            description="Organize entities into meaningful groups based on their relationships and attributes"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={4} align="stretch">
                <Text fontWeight="bold">Current Entity Count:</Text>
                <Badge colorScheme="blue" fontSize="md" p={2}>
                    {mergedEntities.length} Entities Available for Grouping
                </Badge>

                {groups.length > 0 && (
                    <Box mt={4}>
                        <Text fontWeight="bold" mb={4}>Generated Groups:</Text>
                        <SimpleGrid columns={2} spacing={4}>
                            {groups.map((group, index) => (
                                <Box
                                    key={index}
                                    p={4}
                                    borderRadius="md"
                                    bg="white"
                                    shadow="sm"
                                    border="1px"
                                    borderColor="gray.200"
                                >
                                    <Text fontWeight="bold" color="blue.600">
                                        {group.name}
                                    </Text>
                                    <Flex justify="space-between" mt={2}>
                                        <Text fontSize="sm">Entities:</Text>
                                        <Badge colorScheme="green">
                                            {group.entityCount}
                                        </Badge>
                                    </Flex>
                                    <Flex justify="space-between" mt={1}>
                                        <Text fontSize="sm">Confidence:</Text>
                                        <Badge colorScheme={group.confidence > 0.8 ? "green" : "yellow"}>
                                            {(group.confidence * 100).toFixed(1)}%
                                        </Badge>
                                    </Flex>
                                </Box>
                            ))}
                        </SimpleGrid>
                    </Box>
                )}
            </VStack>
        </BaseStage>
    );
};

export default GroupStage;