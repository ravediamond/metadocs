import React, { useState } from 'react';
import { Box, Text, VStack } from '@chakra-ui/react';
import BaseStage from './BaseStage';

const ExtractStage = ({ domainId, pipelineId, onComplete, onPipelineCreate, processing, setProcessing, token, currentTenant }) => {
    const [status, setStatus] = useState('pending');

    const startExtraction = async (pipelineId, token) => {
        await new Promise(resolve => setTimeout(resolve, 3000));
        return {
          entities: [
            { type: "Protocol", name: "Emergency Shutdown", priority: "High" },
            { type: "Equipment", name: "Pressure Regulator", category: "Hardware" }
          ],
          stats: {
            total: 15,
            byType: { Protocol: 5, Equipment: 10 }
          }
        };
      };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');
        try {
            await startExtraction();
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
            title="Extract Entities"
            description="Identify domain-specific entities"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <Box bg="white" rounded="xl" p={6} shadow="sm" borderWidth={1} borderColor="gray.100" fontFamily="mono">
                <Text className="text-sm whitespace-pre-wrap text-gray-800">
{`{
  "entities": [
    {
      "type": "Protocol",
      "name": "Emergency Shutdown",
      "category": "Safety",
      "priority": "High",
      "relatedTo": ["Safety Valve", "Pressure Monitor"],
      "steps": [
        "Close main valve",
        "Depressurize system",
        "Activate alerts"
      ]
    },
    {
      "type": "Equipment",
      "name": "Pressure Regulator",
      "category": "Hardware",
      "maintenanceFreq": "Monthly",
      "specifications": {
        "operatingRange": "0-100 PSI",
        "safetyMargin": "10%",
        "responseTime": "< 1s"
      }
    },
    {
      "type": "MaintenanceTask",
      "name": "Weekly Inspection",
      "frequency": "7d",
      "requiredCert": "Level 2",
      "checkpoints": [
        "Pressure readings",
        "Visual inspection",
        "Sensor calibration"
      ]
    }
  ]
}`}</Text>
            </Box>
        </BaseStage>
    );
};

export default ExtractStage;