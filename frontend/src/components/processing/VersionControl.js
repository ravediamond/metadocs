import React from 'react';
import {
    Box,
    Button,
    Flex,
    Text,
    Badge,
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    IconButton,
    useToast,
    Tooltip,
} from '@chakra-ui/react';
import { ChevronDownIcon, RepeatIcon, CheckIcon, WarningIcon } from '@chakra-ui/icons';

const VersionControl = ({
    currentVersion,
    versions,
    onCreateVersion,
    onSelectVersion,
    onValidateVersion
}) => {
    const toast = useToast();

    const handleCreateVersion = async () => {
        try {
            await onCreateVersion();
            toast({
                title: 'New version created',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            toast({
                title: 'Error creating version',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleValidateVersion = async () => {
        if (!currentVersion) {
            toast({
                title: 'No version selected',
                description: 'Please select a version to validate',
                status: 'warning',
                duration: 3000,
                isClosable: true,
            });
            return;
        }

        try {
            await onValidateVersion(currentVersion.id);
            toast({
                title: 'Version validated',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            toast({
                title: 'Error validating version',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    return (
        <Box bg="gray.50" p={4} borderRadius="md" mb={4}>
            <Flex justify="space-between" align="center">
                <Box>
                    <Text fontWeight="bold" mb={2}>Version Control</Text>
                    {currentVersion ? (
                        <Flex align="center" gap={2}>
                            <Text>Current Version: {currentVersion.number}</Text>
                            <Badge
                                colorScheme={
                                    currentVersion.status === 'validated'
                                        ? 'green'
                                        : currentVersion.status === 'draft'
                                            ? 'yellow'
                                            : 'blue'
                                }
                            >
                                {currentVersion.status}
                            </Badge>
                            {currentVersion.status === 'validated' && (
                                <Tooltip label="Validated">
                                    <CheckIcon color="green.500" />
                                </Tooltip>
                            )}
                        </Flex>
                    ) : (
                        <Text color="gray.500">No version selected</Text>
                    )}
                </Box>

                <Flex gap={2}>
                    <Menu>
                        <MenuButton
                            as={Button}
                            rightIcon={<ChevronDownIcon />}
                            variant="outline"
                        >
                            Select Version
                        </MenuButton>
                        <MenuList>
                            {versions?.map((version) => (
                                <MenuItem
                                    key={version.id}
                                    onClick={() => onSelectVersion(version)}
                                    icon={
                                        version.status === 'validated' ? (
                                            <CheckIcon color="green.500" />
                                        ) : version.status === 'draft' ? (
                                            <WarningIcon color="yellow.500" />
                                        ) : (
                                            <RepeatIcon color="blue.500" />
                                        )
                                    }
                                >
                                    Version {version.number}{' '}
                                    <Badge ml={2} colorScheme={version.status === 'validated' ? 'green' : 'yellow'}>
                                        {version.status}
                                    </Badge>
                                </MenuItem>
                            ))}
                        </MenuList>
                    </Menu>

                    <Button
                        colorScheme="blue"
                        onClick={handleCreateVersion}
                    >
                        Create New Version
                    </Button>

                    <Button
                        colorScheme="green"
                        onClick={handleValidateVersion}
                        isDisabled={!currentVersion || currentVersion.status === 'validated'}
                    >
                        Validate Version
                    </Button>
                </Flex>
            </Flex>

            {currentVersion?.lastModified && (
                <Text fontSize="sm" color="gray.500" mt={2}>
                    Last modified: {new Date(currentVersion.lastModified).toLocaleString()}
                </Text>
            )}
        </Box>
    );
};

export default VersionControl;