import React from 'react';
import { Box, Flex, Text, Progress, VStack } from '@chakra-ui/react';

const ProcessingProgress = ({ currentStage, results }) => {
    // Simplified list of stages
    const stages = ['PARSE', 'EXTRACT', 'GRAPH'];

    const getStageStatus = (stage) => {
        const lowerStage = stage.toLowerCase();
        const stageIndex = stages.indexOf(stage);
        const currentStageIndex = stages.indexOf(currentStage);
        // Determine if stage has results
        const hasResults = results && results[lowerStage];

        if (currentStage === 'COMPLETED') {
            return {
                color: hasResults ? "green" : "gray",
                progress: hasResults ? 100 : 0,
                isIndeterminate: false
            };
        }

        // Stage is current
        if (stage === currentStage) {
            return {
                color: "blue",
                progress: 0,
                isIndeterminate: true
            };
        }

        // Stage is completed
        if (stageIndex < currentStageIndex && hasResults) {
            return {
                color: "green",
                progress: 100,
                isIndeterminate: false
            };
        }

        // Stage is pending
        return {
            color: "gray",
            progress: 0,
            isIndeterminate: false
        };
    };

    return (
        <VStack spacing={6} w="full" p={6} bg="white" rounded="lg" h="full" shadow="sm">
            <Text fontSize="lg" fontWeight="medium">Processing Pipeline</Text>
            {stages.map((stage) => {
                const status = getStageStatus(stage);
                return (
                    <Box key={stage} w="full">
                        <Flex justify="space-between" mb={2}>
                            <Text>{stage}</Text>
                            {status.progress === 100 && (
                                <Text fontSize="sm" color="green.500">
                                    Completed
                                </Text>
                            )}
                        </Flex>
                        <Progress
                            size="sm"
                            colorScheme={status.color}
                            isIndeterminate={status.isIndeterminate}
                            value={status.progress}
                            borderRadius="full"
                        />
                        {stage === currentStage && !status.isIndeterminate && (
                            <Text fontSize="xs" color="gray.500" mt={1}>
                                Processing...
                            </Text>
                        )}
                    </Box>
                );
            })}
        </VStack>
    );
};

export default ProcessingProgress;