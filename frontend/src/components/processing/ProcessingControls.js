import React from 'react';
import {
    Box,
    Button,
    HStack,
    Alert,
    AlertIcon,
    AlertTitle,
    AlertDescription,
} from '@chakra-ui/react';

const ProcessingControls = ({
    isRunning,
    error,
    onStart,
    onStop,
    isStartDisabled
}) => {
    return (
        <Box>
            <HStack spacing={4} mb={4}>
                <Button
                    colorScheme="blue"
                    onClick={onStart}
                    isDisabled={isStartDisabled || isRunning}
                >
                    Start Processing
                </Button>
                <Button
                    colorScheme="red"
                    onClick={onStop}
                    isDisabled={!isRunning}
                >
                    Stop Processing
                </Button>
            </HStack>

            {error && (
                <Alert status="error" mt={4}>
                    <AlertIcon />
                    <AlertTitle>Error:</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}
        </Box>
    );
};

export default ProcessingControls;