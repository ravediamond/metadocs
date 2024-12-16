import React from 'react';
import { Box, VStack, Text, Badge, Progress, Button, Flex } from '@chakra-ui/react';
import { marked } from 'marked';

const StageDetailPanel = ({
    stage,
    files,
    results,
    isLoading,
    logs,
    onViewLog,
    activeFile,
    setActiveFile
}) => {
    // Helper function to get status color
    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return 'green';
            case 'in_progress': return 'blue';
            case 'error': return 'red';
            default: return 'gray';
        }
    };

    return (
        <Box bg="white" rounded="lg" shadow="sm" p={4} h="full">
            <VStack spacing={4} align="stretch">
                {/* Stage Header */}
                <Flex justify="space-between" align="center">
                    <Text fontSize="lg" fontWeight="bold">
                        {stage.label} Results
                    </Text>
                    <Badge colorScheme={getStatusColor(stage.status)}>
                        {stage.status}
                    </Badge>
                </Flex>

                {/* Progress Indicator */}
                {isLoading && <Progress size="xs" isIndeterminate />}

                {/* File List */}
                {files?.length > 0 && (
                    <Box>
                        <Text fontWeight="medium" mb={2}>Files:</Text>
                        <VStack align="stretch">
                            {files.map((file) => (
                                <Box
                                    key={file.id}
                                    p={2}
                                    bg={activeFile?.id === file.id ? 'blue.50' : 'gray.50'}
                                    rounded="md"
                                    cursor="pointer"
                                    onClick={() => setActiveFile(file)}
                                >
                                    <Flex justify="space-between" align="center">
                                        <Text>{file.filename}</Text>
                                        <Badge colorScheme={getStatusColor(file.status)}>
                                            {file.status}
                                        </Badge>
                                    </Flex>
                                </Box>
                            ))}
                        </VStack>
                    </Box>
                )}

                {/* Results Viewer */}
                {activeFile && results?.[activeFile.id] && (
                    <Box flex="1" overflowY="auto">
                        <Text fontWeight="medium" mb={2}>Content:</Text>
                        <Box
                            p={4}
                            bg="gray.50"
                            rounded="md"
                            maxH="600px"
                            overflowY="auto"
                        >
                            <div
                                className="markdown-content"
                                dangerouslySetInnerHTML={{
                                    __html: marked(results[activeFile.id])
                                }}
                            />
                        </Box>
                    </Box>
                )}

                {/* Log Viewer */}
                {logs?.[activeFile?.id] && (
                    <Box>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onViewLog(activeFile.id)}
                        >
                            View Logs
                        </Button>
                    </Box>
                )}
            </VStack>
        </Box>
    );
};

export default StageDetailPanel;