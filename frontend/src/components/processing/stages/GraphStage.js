import React, { useState } from 'react';
import { Box, Text, Button, HStack, VStack } from '@chakra-ui/react';
import { Download, Eye } from 'lucide-react';
import BaseStage from './BaseStage';

const GraphStage = ({ domainId, pipelineId, onComplete, onPipelineCreate, processing, setProcessing, token, currentTenant }) => {
    const [status, setStatus] = useState('pending');

    const generateGraph = async (pipelineId, token) => {
        await new Promise(resolve => setTimeout(resolve, 4000));
        return {
          nodes: 65,
          edges: 128,
          clusters: 6,
          density: 0.42
        };
      };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');
        try {
            await generateGraph();
            setStatus('completed');
            onComplete();
        } catch (error) {
            setStatus('failed');
        } finally {
            setProcessing(false);
        }
    };

    return (
        <BaseStage
            title="Knowledge Graph"
            description="Generate final knowledge graph"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={4}>
                <Box bg="white" rounded="xl" p={6} shadow="sm" borderWidth={1} borderColor="gray.100" w="full" fontFamily="mono">
                    <Text className="text-sm whitespace-pre-wrap text-gray-800">
{`graph TD
    A[Gas Distribution] -->|includes| B[Safety Procedures]
    A -->|uses| C[Equipment]
    A -->|requires| D[Maintenance]
    
    B -->|has| E[Emergency Shutdown]
    B -->|has| F[Leak Detection]
    
    C -->|contains| G[Pressure Regulator]
    C -->|contains| H[Safety Valve]
    
    D -->|schedules| I[Daily Checks]
    D -->|schedules| J[Weekly Inspection]
    
    G -->|requires| D
    H -->|requires| D`}</Text>
                </Box>

                {status === 'completed' && (
                    <HStack spacing={4} w="full">
                        <Button leftIcon={<Eye size={20} />} flex={1}>View Graph</Button>
                        <Button leftIcon={<Download size={20} />} flex={1}>Download Graph</Button>
                    </HStack>
                )}
            </VStack>
        </BaseStage>
    );
};

export default GraphStage;