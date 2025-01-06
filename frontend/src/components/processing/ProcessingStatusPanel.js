import React from 'react';
import { Box, Flex, Text } from '@chakra-ui/react';
import MermaidDiagram from '../visualizations/MermaidDiagram';
import CodeVisualization from '../visualizations/CodeVisualization';
import MarkdownVisualization from '../visualizations/MarkdownVisualization';
import ProcessingProgress from './ProcessingProgress';

const ProcessingStatusPanel = ({ isRunning, currentStage, results, visualization }) => {
    console.log('ProcessingStatusPanel received props:', { visualization, results });

    // If processing is running, show progress
    if (isRunning) {
        return <ProcessingProgress currentStage={currentStage} results={results} />;
    }

    // If we have a specific visualization, show it
    if (visualization?.type !== 'none' && visualization?.content) {
        switch (visualization.type) {
            case 'mermaid':
                return (
                    <Box bg="white" rounded="lg" p={4} h="full" shadow="sm">
                        <MermaidDiagram diagram={visualization.content} />
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

    // Default to graph visualization if available
    if (results?.graph?.visualization) {
        return (
            <Box bg="white" rounded="lg" p={4} h="full" shadow="sm">
                <MermaidDiagram diagram={results.graph.visualization} />
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