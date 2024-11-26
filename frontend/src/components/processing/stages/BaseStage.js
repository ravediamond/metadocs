import React from 'react';
import {
    VStack,
    Text,
    Button,
    Badge,
    Box,
    Progress,
} from '@chakra-ui/react';

const BaseStage = ({
    title,
    description,
    status = 'pending', // pending, processing, completed, failed
    onStart,
    onRetry,
    processing = false,
    children
}) => {
    // Helper function for badge color
    const getBadgeColor = (status) => {
        switch (status) {
            case 'completed':
                return 'green';
            case 'processing':
                return 'blue';
            case 'failed':
                return 'red';
            default:
                return 'gray';
        }
    };

    return (
        <VStack spacing={6} align="stretch">
            {/* Header */}
            <Box>
                <Text fontSize="xl" fontWeight="bold" mb={2}>{title}</Text>
                <Text color="gray.600" mb={4}>{description}</Text>
                <Badge colorScheme={getBadgeColor(status)}>
                    {status}
                </Badge>
            </Box>

            {/* Processing Progress */}
            {processing && (
                <Progress size="sm" isIndeterminate colorScheme="blue" />
            )}

            {/* Main Content */}
            <Box>{children}</Box>

            {/* Actions */}
            <Box>
                <Button
                    colorScheme="blue"
                    onClick={status === 'failed' ? onRetry : onStart}
                    isDisabled={processing || status === 'completed'}
                    isLoading={processing}
                >
                    {status === 'failed' ? 'Retry' : 'Start Processing'}
                </Button>

                {status === 'completed' && (
                    <Button
                        ml={4}
                        variant="outline"
                        onClick={onRetry}
                    >
                        Reprocess
                    </Button>
                )}
            </Box>
        </VStack>
    );
};

export default BaseStage;