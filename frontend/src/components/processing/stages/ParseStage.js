import React, { useState, useEffect } from 'react';
import {
    Box,
    VStack,
    Text,
    List,
    ListItem,
    Flex,
    Icon,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import BaseStage from './BaseStage';

const ParseStage = ({
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

    useEffect(() => {
        // Fetch files for the current domain
        fetchFiles();
    }, [domainId]);

    const fetchFiles = async () => {
        try {
            const response = await fetch(`/api/domains/${domainId}/files`);
            const data = await response.json();
            setFiles(data);
        } catch (error) {
            console.error('Error fetching files:', error);
        }
    };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            // Start processing for each file
            for (const file of files) {
                const response = await fetch(
                    `/api/domains/${domainId}/files/${file.id}/parse`,
                    {
                        method: 'POST',
                    }
                );
                const data = await response.json();

                // Update progress
                setProgress(prev => ({
                    ...prev,
                    [file.id]: {
                        status: 'completed',
                        pipeline: data.pipeline_id,
                    }
                }));
            }

            setStatus('completed');
            onComplete();
        } catch (error) {
            setStatus('failed');
            console.error('Error during parsing:', error);
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
            <VStack spacing={4} align="stretch">
                <Text fontWeight="bold">Files to Process:</Text>
                <List spacing={3}>
                    {files.map((file) => (
                        <ListItem key={file.id}>
                            <Flex justify="space-between" align="center">
                                <Text>{file.name}</Text>
                                <Icon
                                    as={progress[file.id]?.status === 'completed' ? CheckCircleIcon : WarningIcon}
                                    color={progress[file.id]?.status === 'completed' ? 'green.500' : 'yellow.500'}
                                />
                            </Flex>
                        </ListItem>
                    ))}
                </List>
            </VStack>
        </BaseStage>
    );
};

export default ParseStage;