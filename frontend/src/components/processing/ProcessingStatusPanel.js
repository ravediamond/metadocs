import React from 'react';
import { Box, Flex, Text, Progress, VStack } from '@chakra-ui/react';
import MermaidDiagram from './MermaidDiagram';

const ProcessingStatusPanel = ({ isRunning, currentStage, results }) => {
    // Show processing status or ontology diagram
    if (isRunning) {
        return (
            <VStack spacing={6} w="full" p={6} bg="white" rounded="lg" h="full" shadow="sm">
                <Text fontSize="lg" fontWeight="medium">Processing Pipeline</Text>
                {['PARSE', 'EXTRACT', 'MERGE', 'GROUP', 'ONTOLOGY'].map((stage) => (
                    <Box key={stage} w="full">
                        <Flex justify="space-between" mb={2}>
                            <Text>{stage}</Text>
                        </Flex>
                        <Progress
                            size="sm"
                            colorScheme={stage === currentStage ? "blue" :
                                currentStage === 'COMPLETED' && results[stage.toLowerCase()] ? "green" : "gray"}
                            isIndeterminate={stage === currentStage}
                            value={currentStage === 'COMPLETED' && results[stage.toLowerCase()] ? 100 :
                                stage === currentStage ? 0 :
                                    results[stage.toLowerCase()] ? 100 : 0}
                        />
                    </Box>
                ))}
            </VStack>
        );
    }

    // Show ontology diagram if we have results
    const ontologyContent = results?.ontology;
    if (ontologyContent) {
        // Handle the case where ontologyContent is an object with an ontology property
        const diagramContent = typeof ontologyContent === 'object' && 'ontology' in ontologyContent
            ? ontologyContent.ontology
            : ontologyContent;

        // If the diagram content is empty, show a message
        if (!diagramContent || diagramContent === '') {
            return (
                <Flex justify="center" align="center" h="full" bg="white" rounded="lg" shadow="sm">
                    <Text color="gray.500">
                        No ontology diagram data available
                    </Text>
                </Flex>
            );
        }

        return (
            <Box bg="white" rounded="lg" p={4} h="full" shadow="sm">
                <MermaidDiagram diagram={diagramContent} />
            </Box>
        );
    }

    // Default state
    return (
        <Flex justify="center" align="center" h="full" bg="white" rounded="lg" shadow="sm">
            <Text color="gray.500">
                Start processing to generate the ontology diagram
            </Text>
        </Flex>
    );
};

export default ProcessingStatusPanel;