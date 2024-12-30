import React from 'react';
import { Box, Text, Spinner, Flex } from '@chakra-ui/react';
import { ForceGraph2D } from 'react-force-graph';

const ForceGraph = ({ data }) => {
    if (!data) {
        return (
            <Flex justify="center" align="center" height="100%" minH="300px">
                <Text color="gray.500">No graph data available</Text>
            </Flex>
        );
    }

    try {
        // Parse the data if it's a string
        const graphData = typeof data === 'string' ? JSON.parse(data) : data;

        // Transform data for force-graph format
        const nodes = Object.entries(graphData.entities || {}).map(([id, entity]) => ({
            id,
            name: entity.name || id,
            category: entity.category || 'unknown',
            val: 1
        }));

        const links = (graphData.relationships || []).map(rel => ({
            source: rel.source,
            target: rel.target,
            type: rel.type || 'related'
        }));

        const processedData = {
            nodes,
            links
        };

        return (
            <Box height="600px" width="100%">
                <ForceGraph2D
                    graphData={processedData}
                    nodeLabel={node => `${node.name} (${node.category})`}
                    linkLabel={link => link.type}
                    nodeAutoColorBy="category"
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                    cooldownTicks={100}
                />
            </Box>
        );
    } catch (error) {
        console.error('Error processing graph data:', error);
        return (
            <Flex justify="center" align="center" height="100%" minH="300px">
                <Text color="red.500">Error processing graph data: {error.message}</Text>
            </Flex>
        );
    }
};

export default ForceGraph;