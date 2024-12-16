import React from 'react';
import {
    Box,
    Button,
    VStack,
    Text,
    Progress,
    Badge,
    Flex,
    Tooltip,
} from '@chakra-ui/react';
import { Play, Square, AlertCircle } from 'lucide-react';

const ProcessingControls = ({
    isRunning,
    currentStage,
    progress,
    error,
    onStart,
    onStop,
    isStartDisabled
}) => {
    return (
        <Box bg="white" rounded="lg" shadow="sm" p={4}>
            <VStack spacing={4} align="stretch">
                {/* Status Section */}
                <Flex justify="space-between" align="center">
                    <Text fontSize="lg" fontWeight="bold">Pipeline Control</Text>
                    <Badge
                        colorScheme={isRunning ? 'green' : error ? 'red' : 'gray'}
                    >
                        {isRunning ? 'Running' : error ? 'Error' : 'Ready'}
                    </Badge>
                </Flex>

                {/* Progress */}
                {isRunning && (
                    <Box>
                        <Text fontSize="sm" mb={1}>
                            Processing: {currentStage}
                        </Text>
                        <Progress
                            value={progress}
                            size="xs"
                            colorScheme="blue"
                        />
                    </Box>
                )}

                {/* Error Display */}
                {error && (
                    <Flex
                        bg="red.50"
                        p={2}
                        rounded="md"
                        align="center"
                        gap={2}
                    >
                        <AlertCircle size={16} color="red" />
                        <Text fontSize="sm" color="red.600">{error}</Text>
                    </Flex>
                )}

                {/* Control Buttons */}
                <Flex gap={2}>
                    <Tooltip label={isStartDisabled ? "Select files to start processing" : ""}>
                        <Button
                            leftIcon={<Play size={16} />}
                            colorScheme="blue"
                            isDisabled={isRunning || isStartDisabled}
                            onClick={onStart}
                            flex="1"
                        >
                            Start Pipeline
                        </Button>
                    </Tooltip>

                    <Button
                        leftIcon={<Square size={16} />}
                        variant="outline"
                        colorScheme="red"
                        isDisabled={!isRunning}
                        onClick={onStop}
                    >
                        Stop
                    </Button>
                </Flex>
            </VStack>
        </Box>
    );
};

export default ProcessingControls;