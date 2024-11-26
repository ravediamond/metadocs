import React, { useState, useEffect } from 'react';
import {
    VStack,
    Text,
    List,
    ListItem,
    Flex,
    Icon,
    Badge,
    Box,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import BaseStage from './BaseStage';

const ExtractStage = ({
    domainId,
    version,
    pipelineId,
    onComplete,
    onPipelineCreate,
    processing,
    setProcessing,
}) => {
    const [status, setStatus] = useState('pending');
    const [files, setFiles] = useState([]);
    const [progress, setProgress] = useState({});
    const [entities, setEntities] = useState([]);

    useEffect(() => {
        fetchParsedFiles();
    }, [domainId]);

    const fetchParsedFiles = async () => {
        try {
            const response = await fetch(`/api/domains/${domainId}/files?status=parsed`);
            const data = await response.json();
            setFiles(data);
        } catch (error) {
            console.error('Error fetching parsed files:', error);
        }
    };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            for (const file of files) {
                const response = await fetch(
                    `/api/domains/${domainId}/files/${file.id}/extract`,
                    {
                        method: 'POST',
                    }
                );
                const data = await response.json();

                setProgress(prev => ({
                    ...prev,
                    [file.id]: {
                        status: 'completed',
                        pipeline: data.pipeline_id,
                        entityCount: data.entityCount
                    }
                }));

                // Simulate receiving extracted entities
                setEntities(prev => [
                    ...prev,
                    { type: 'Product', count: Math.floor(Math.random() * 20) },
                    { type: 'Process', count: Math.floor(Math.random() * 15) },
                    { type: 'Stakeholder', count: Math.floor(Math.random() * 10) },
                ]);
            }

            setStatus('completed');
            onComplete();
        } catch (error) {
            setStatus('failed');
            console.error('Error during extraction:', error);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <BaseStage
            title="Extract Entities"
            description="Identify and extract domain-specific entities from processed documents"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={4} align="stretch">
                <Text fontWeight="bold">Files for Entity Extraction:</Text>
                <List spacing={3}>
                    {files.map((file) => (
                        <ListItem key={file.id}>
                            <Flex justify="space-between" align="center">
                                <Text>{file.name}</Text>
                                <Flex align="center" gap={2}>
                                    {progress[file.id]?.entityCount && (
                                        <Badge colorScheme="blue">
                                            {progress[file.id].entityCount} entities
                                        </Badge>
                                    )}
                                    <Icon
                                        as={progress[file.id]?.status === 'completed' ? CheckCircleIcon : WarningIcon}
                                        color={progress[file.id]?.status === 'completed' ? 'green.500' : 'yellow.500'}
                                    />
                                </Flex>
                            </Flex>
                        </ListItem>
                    ))}
                </List>

                {entities.length > 0 && (
                    <Box mt={4}>
                        <Text fontWeight="bold" mb={2}>Extracted Entities:</Text>
                        <List spacing={2}>
                            {entities.map((entity, index) => (
                                <ListItem key={index}>
                                    <Flex justify="space-between">
                                        <Text>{entity.type}</Text>
                                        <Badge colorScheme="green">{entity.count}</Badge>
                                    </Flex>
                                </ListItem>
                            ))}
                        </List>
                    </Box>
                )}
            </VStack>
        </BaseStage>
    );
};

export default ExtractStage;