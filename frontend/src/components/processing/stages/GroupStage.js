import React, { useState } from 'react';
import { Box, Text, VStack } from '@chakra-ui/react';
import BaseStage from './BaseStage';

const GroupStage = ({ domainId, pipelineId, onComplete, onPipelineCreate, processing, setProcessing, token, currentTenant }) => {
    const [status, setStatus] = useState('pending');

    const generateGroups = async (pipelineId, token) => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        return {
          groups: [
            { name: "Safety Procedures", entities: ["Emergency_Shutdown", "Leak_Detection"] },
            { name: "Equipment", entities: ["Pressure_Regulator", "Safety_Valve"] }
          ],
          stats: {
            totalGroups: 4,
            totalEntities: 16
          }
        };
      };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');
        try {
            await generateGroups();
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
            title="Group Concepts"
            description="Organize entities into meaningful groups"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <VStack spacing={6}>
                <Box bg="white" p={6} rounded="xl" shadow="sm" borderWidth={1} borderColor="gray.100" w="full">
                    <VStack align="stretch" spacing={6}>
                        <Box>
                            <Text fontWeight="medium" mb={2}>Safety Procedures</Text>
                            <Box className="flex flex-wrap gap-2">
                                <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-lg text-sm">Emergency_Shutdown</span>
                                <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-lg text-sm">Leak_Detection</span>
                                <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-lg text-sm">Evacuation</span>
                                <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-lg text-sm">Safety_Check</span>
                            </Box>
                        </Box>

                        <Box>
                            <Text fontWeight="medium" mb={2}>Equipment</Text>
                            <Box className="flex flex-wrap gap-2">
                                <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm">Pressure_Regulator</span>
                                <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm">Safety_Valve</span>
                                <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm">Monitoring_System</span>
                            </Box>
                        </Box>

                        <Box>
                            <Text fontWeight="medium" mb={2}>Maintenance</Text>
                            <Box className="flex flex-wrap gap-2">
                                <span className="px-3 py-1 bg-green-50 text-green-700 rounded-lg text-sm">Daily_Inspection</span>
                                <span className="px-3 py-1 bg-green-50 text-green-700 rounded-lg text-sm">Weekly_Check</span>
                                <span className="px-3 py-1 bg-green-50 text-green-700 rounded-lg text-sm">Monthly_Service</span>
                            </Box>
                        </Box>

                        <Box>
                            <Text fontWeight="medium" mb={2}>Certifications</Text>
                            <Box className="flex flex-wrap gap-2">
                                <span className="px-3 py-1 bg-orange-50 text-orange-700 rounded-lg text-sm">Safety_Certificate</span>
                                <span className="px-3 py-1 bg-orange-50 text-orange-700 rounded-lg text-sm">Operation_License</span>
                                <span className="px-3 py-1 bg-orange-50 text-orange-700 rounded-lg text-sm">Technical_Approval</span>
                            </Box>
                        </Box>
                    </VStack>
                </Box>
            </VStack>
        </BaseStage>
    );
};

export default GroupStage;