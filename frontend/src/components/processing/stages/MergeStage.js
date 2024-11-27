import React, { useState } from 'react';
import { Box, VStack, Button, Text, HStack } from '@chakra-ui/react';
import BaseStage from './BaseStage';

const MergeStage = ({ domainId, pipelineId, onComplete, onPipelineCreate, processing, setProcessing, token, currentTenant }) => {
    const [status, setStatus] = useState('pending');

    const mergePipeline = async (pipelineId, token) => {
        await new Promise(resolve => setTimeout(resolve, 2500));
        return {
          mergedEntities: [
            { source: "EmergencyShutdown_1", target: "ShutdownProcedure_2" },
            { source: "PressureValve_A", target: "SafetyValve_B" }
          ],
          stats: {
            totalMerged: 12,
            duplicatesRemoved: 6
          }
        };
      };

      const createPipeline = async (tenant, domain, stage, token) => {
        const response = await fetch(`/api/pipeline/create`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: JSON.stringify({ tenant, domain, stage })
        });
        return response.json();
      };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');
        try {
            const pipelineData = await createPipeline();
            await mergePipeline(pipelineData.pipeline_id);
            setStatus('completed');
            onComplete();
        } catch (error) {
            setStatus('failed');
        } finally {
            setProcessing(false);
        }
    };

    const renderSuggestedMerge = (source, target) => (
        <Box className="flex items-center justify-between p-2 bg-white rounded border border-blue-200">
            <Text className="text-sm font-mono">{source}</Text>
            <Text className="text-gray-400">→</Text>
            <Text className="text-sm font-mono">{target}</Text>
            <Button size="sm" variant="ghost" colorScheme="blue">
                Merge
            </Button>
        </Box>
    );

    return (
        <BaseStage
            title="Merge Entities"
            description="Combine and deduplicate entities"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={4}>
                {/* Suggested Merges Section */}
                <Box className="w-full bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <Box className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                        <HStack justify="space-between" mb={3}>
                            <Text className="font-medium text-blue-900">Suggested Merges</Text>
                            <Button size="sm" colorScheme="blue">Apply All</Button>
                        </HStack>
                        <VStack spacing={2}>
                            {renderSuggestedMerge("EmergencyShutdown_1", "ShutdownProcedure_2")}
                            {renderSuggestedMerge("PressureValve_A", "SafetyValve_B")}
                            {renderSuggestedMerge("LeakDetector_1", "GasDetector_2")}
                            {renderSuggestedMerge("MaintenanceTask_5", "RepairTask_3")}
                        </VStack>
                    </Box>
                </Box>

                {/* Similar Entities Section */}
                <Box className="w-full bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <Text className="font-medium mb-4">Similar Entity Groups</Text>
                    <VStack spacing={3}>
                        <Box className="w-full p-3 bg-gray-50 rounded-lg">
                            <Text className="font-medium mb-2">Safety Protocols</Text>
                            <Text className="text-sm text-gray-600">
                                3 similar entities found
                            </Text>
                        </Box>
                        <Box className="w-full p-3 bg-gray-50 rounded-lg">
                            <Text className="font-medium mb-2">Maintenance Procedures</Text>
                            <Text className="text-sm text-gray-600">
                                5 similar entities found
                            </Text>
                        </Box>
                    </VStack>
                </Box>
            </VStack>
        </BaseStage>
    );
};

export default MergeStage;