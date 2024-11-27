import React, { useState } from 'react';
import { Box, Text, VStack } from '@chakra-ui/react';
import BaseStage from './BaseStage';

const ParseStage = ({ domainId, pipelineId, onComplete, onPipelineCreate, processing, setProcessing, token, currentTenant }) => {
    const [status, setStatus] = useState('pending');

    const parsePipeline = async (pipelineId, token) => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        return {
          documents: 5,
          totalPages: 25,
          formats: { pdf: 3, docx: 2 }
        };
      };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');
        try {
            await parsePipeline();
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
            title="Parse Documents"
            description="Convert documents into processable text"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <Box bg="white" rounded="xl" p={6} shadow="sm" borderWidth={1} borderColor="gray.100" fontFamily="mono">
                <Text className="text-sm whitespace-pre-wrap text-gray-800">
{`# Gas Distribution System Documentation

## Safety Protocols
- Emergency shutdown procedures
  - Immediate valve closure
  - System depressurization
  - Alert notification

- Leak detection and response
  - Continuous monitoring
  - Threshold alerts
  - Response procedures

## Maintenance Schedule
- Daily inspections
  - Pressure readings
  - Visual checks
  - Sensor validation

- Weekly pressure checks
  - System calibration
  - Performance testing
  - Safety verification

## Equipment Specifications
- Pressure regulators
  - Operating range: 0-100 PSI
  - Safety margins
  - Response times

- Safety valves
  - Activation thresholds
  - Redundancy systems
  - Testing requirements`}</Text>
            </Box>
        </BaseStage>
    );
};

export default ParseStage;