import React from 'react';
import {
    Box,
    Text,
    VStack,
    Heading,
    Badge,
    Button,
    Progress,
    HStack,
    IconButton,
    useColorModeValue
} from '@chakra-ui/react';
import { RepeatIcon, CopyIcon } from '@chakra-ui/icons';

const BaseStage = ({
    title,
    description,
    status = 'pending',
    onStart,
    onRetry,
    processing = false,
    children
}) => {
    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.100', 'gray.700');

    const getBadgeColor = (status) => {
        switch (status) {
            case 'completed': return 'green';
            case 'processing': return 'blue';
            case 'failed': return 'red';
            default: return 'gray';
        }
    };

    return (
        <Box bg={bgColor} rounded="xl" shadow="sm" borderWidth={1} borderColor={borderColor}>
            {processing && (
                <Progress 
                    size="xs" 
                    isIndeterminate 
                    colorScheme="blue"
                    rounded="xl"
                />
            )}
            
            <Box p={6}>
                <VStack spacing={6} align="stretch">
                    {/* Header */}
                    <HStack justify="space-between">
                        <VStack align="start" spacing={1}>
                            <Heading size="md">{title}</Heading>
                            <Text color="gray.600" fontSize="sm">{description}</Text>
                        </VStack>
                        <Badge 
                            colorScheme={getBadgeColor(status)}
                            px={3}
                            py={1}
                            rounded="full"
                        >
                            {status}
                        </Badge>
                    </HStack>

                    {/* Content */}
                    <Box>{children}</Box>

                    {/* Actions */}
                    <HStack justify="space-between">
                        <HStack spacing={2}>
                            <IconButton
                                icon={<RepeatIcon />}
                                aria-label="Retry"
                                variant="ghost"
                                isDisabled={processing}
                                onClick={onRetry}
                            />
                            <IconButton
                                icon={<CopyIcon />}
                                aria-label="Copy"
                                variant="ghost"
                            />
                        </HStack>
                        
                        <Button
                            colorScheme="blue"
                            onClick={status === 'failed' ? onRetry : onStart}
                            isDisabled={processing || status === 'completed'}
                            isLoading={processing}
                            rounded="xl"
                        >
                            {status === 'failed' ? 'Retry' : 'Start Processing'}
                        </Button>
                    </HStack>
                </VStack>
            </Box>
        </Box>
    );
};

export default BaseStage;