import React from 'react';
import {
    Box,
    Button,
    VStack,
    Text,
    Heading,
    HStack,
    Badge,
    Progress,
} from '@chakra-ui/react';

const BaseStage = ({
    title,
    description,
    status,
    onStart,
    onRetry,
    canProceed,
    processing,
    children,
}) => {
    return (
        <VStack spacing={6} align="stretch">
            <Box>
                <Heading size="md" mb={2}>{title}</Heading>
                <Text color="gray.600">{description}</Text>
            </Box>

            <HStack>
                <Badge
                    colorScheme={
                        status === 'completed'
                            ? 'green'
                            : status === 'processing'
                                ? 'blue'
                                : status === 'failed'
                                    ? 'red'
                                    : 'gray'
                    }
                >
                    {status}
                </Badge>
            </HStack>

            {processing && <Progress size="sm" isIndeterminate />}

            <Box>{children}</Box>

            <HStack spacing={4}>
                <Button
                    colorScheme="blue"
                    onClick={onStart}
                    isDisabled={processing || status === 'completed'}
                >
                    {status === 'failed' ? 'Retry' : 'Start Processing'}
                </Button>
                {status === 'completed' && (
                    <Button
                        colorScheme="green"
                        onClick={onRetry}
                    >
                        Reprocess
                    </Button>
                )}
            </HStack>
        </VStack>
    );
};

export default BaseStage;