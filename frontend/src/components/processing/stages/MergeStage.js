import React, { useState, useEffect } from 'react';
import {
    VStack,
    Text,
    List,
    ListItem,
    Flex,
    Icon,
    Progress,
    Box,
    Badge,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import BaseStage from './BaseStage';

const MergeStage = ({
    domainId,
    version,
    pipelineId,
    onComplete,
    onPipelineCreate,
    processing,
    setProcessing,
}) => {
    const [status, setStatus] = useState('pending');
    const [mergeStats, setMergeStats] = useState(null);
    const [entitySets, setEntitySets] = useState([]);

    useEffect(() => {
        fetchEntitySets();
    }, [domainId]);

    const fetchEntitySets = async () => {
        try {
            const response = await fetch(`/api/domains/${domainId}/entities`);
            const data = await response.json();
            setEntitySets(data);
        } catch (error) {
            console.error('Error fetching entity sets:', error);
        }
    };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            const response = await fetch(
                `/api/domains/${domainId}/merge`,
                {
                    method: 'POST',
                }
            );
            const data = await response.json();

            // Simulate merge statistics
            setMergeStats({
                totalEntities: 150,
                mergedEntities: 120,
                duplicatesRemoved: 30,
                confidence: 0.85
            });

            setStatus('completed');
            onComplete();
        } catch (error) {
            setStatus('failed');
            console.error('Error during merging:', error);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <BaseStage
            title="Merge Knowledge"
            description="Combine and deduplicate entities across documents"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={4} align="stretch">
                <Text fontWeight="bold">Entity Sets to Merge:</Text>
                <List spacing={3}>
                    {entitySets.map((set, index) => (
                        <ListItem key={index}>
                            <Flex justify="space-between" align="center">
                                <Text>Entity Set {index + 1}</Text>
                                <Badge colorScheme="blue">
                                    {set.entityCount} entities
                                </Badge>
                            </Flex>
                        </ListItem>
                    ))}
                </List>

                {mergeStats && (
                    <Box mt={4} p={4} borderRadius="md" bg="gray.50">
                        <Text fontWeight="bold" mb={2}>Merge Statistics:</Text>
                        <List spacing={2}>
                            <ListItem>
                                <Flex justify="space-between">
                                    <Text>Total Entities:</Text>
                                    <Badge>{mergeStats.totalEntities}</Badge>
                                </Flex>
                            </ListItem>
                            <ListItem>
                                <Flex justify="space-between">
                                    <Text>Merged Entities:</Text>
                                    <Badge colorScheme="green">{mergeStats.mergedEntities}</Badge>
                                </Flex>
                            </ListItem>
                            <ListItem>
                                <Flex justify="space-between">
                                    <Text>Duplicates Removed:</Text>
                                    <Badge colorScheme="red">{mergeStats.duplicatesRemoved}</Badge>
                                </Flex>
                            </ListItem>
                            <ListItem>
                                <Text mb={1}>Confidence Score:</Text>
                                <Progress
                                    value={mergeStats.confidence * 100}
                                    colorScheme="blue"
                                    hasStripe
                                />
                            </ListItem>
                        </List>
                    </Box>
                )}
            </VStack>
        </BaseStage>
    );
};

export default MergeStage;