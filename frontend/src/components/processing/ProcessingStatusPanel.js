import React from 'react';
import { Box, Flex, Text, Progress, VStack } from '@chakra-ui/react';
import MermaidDiagram from '../visualizations/MermaidDiagram';
import CodeVisualization from '../visualizations/CodeVisualization';
import MarkdownVisualization from '../visualizations/MarkdownVisualization';
import ProcessingProgress from './ProcessingProgress';

const ProcessingStatusPanel = ({ isRunning, currentStage, results, visualization }) => {
    // Helper function to safely extract and validate Mermaid diagram content

    console.log('ProcessingStatusPanel received props:', { visualization, results });
    const getMermaidContent = (content) => {
        if (!content) return null;

        // Handle string content
        if (typeof content === 'string') {
            return content.trim();
        }

        // Handle object with ontology property
        if (typeof content === 'object' && content.ontology) {
            return content.ontology.trim();
        }

        return null;
    };

    // If processing is running, show progress
    if (isRunning) {
        return <ProcessingProgress currentStage={currentStage} results={results} />;
    }

    // If we have a specific visualization, show it
    if (visualization.type !== 'none' && visualization.content) {
        switch (visualization.type) {
            case 'mermaid':
                const mermaidContent = getMermaidContent(visualization.content);
                return (
                    <Box bg="white" rounded="lg" p={4} h="full" shadow="sm">
                        {mermaidContent ? (
                            <MermaidDiagram diagram={mermaidContent} />
                        ) : (
                            <Flex justify="center" align="center" h="full">
                                <Text color="gray.500">Invalid diagram content</Text>
                            </Flex>
                        )}
                    </Box>
                );
            case 'code':
                return (
                    <Box bg="white" rounded="lg" p={4} h="full" shadow="sm">
                        <CodeVisualization code={visualization.content} />
                    </Box>
                );
            case 'markdown':
                return (
                    <Box bg="white" rounded="lg" h="full" shadow="sm">
                        <MarkdownVisualization content={visualization.content} />
                    </Box>
                );
            default:
                return null;
        }
    }

    // Default to ontology diagram if available
    const ontologyContent = getMermaidContent(results?.ontology);
    if (ontologyContent) {
        return (
            <Box bg="white" rounded="lg" p={4} h="full" shadow="sm">
                <MermaidDiagram diagram={ontologyContent} />
            </Box>
        );
    }

    // Fallback state
    return (
        <Flex justify="center" align="center" h="full" bg="white" rounded="lg" shadow="sm">
            <Text color="gray.500">
                Start processing or ask a question to see visualizations
            </Text>
        </Flex>
    );
};

export default ProcessingStatusPanel;