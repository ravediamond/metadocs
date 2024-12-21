import React from 'react';
import { Box, Flex, Heading, Icon, Text, useColorModeValue, Badge } from '@chakra-ui/react';
import { GitCommit, CheckCircle } from 'lucide-react';

const WorkflowStatus = ({ phases, activePhase, setActivePhase, currentWorkflowVersion }) => {
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const getStatusColor = (phase) => {
    switch (phase.status) {
      case 'completed':
        return { bg: 'green.100', color: 'green.600', hover: 'green.200' };
      case 'in_progress':
        return { bg: 'blue.100', color: 'blue.600', hover: 'blue.200' };
      case 'pending':
        return { bg: 'gray.100', color: 'gray.400', hover: 'gray.200' };
      default:
        return { bg: 'gray.100', color: 'gray.400', hover: 'gray.200' };
    }
  };

  return (
    <Box bg="white" rounded="lg" shadow="sm" borderWidth="1px" p="4" mb="6">
      <Flex align="center" justify="space-between" mb="4">
        <Heading size="md">Workflow Status</Heading>
        <Flex align="center" gap="2" fontSize="sm">
          <Icon as={GitCommit} boxSize="4" color="gray.400" />
          <Text color="gray.600">Workflow Version {currentWorkflowVersion}</Text>
        </Flex>
      </Flex>
      <Flex gap="4" justify="space-between">
        {phases.map((phase, index) => {
          const statusColor = getStatusColor(phase);
          return (
            <Flex key={phase.id} align="center" flex="1">
              <Flex
                direction="column"
                align="center"
                flex="1"
                cursor="pointer"
                role="group"
                onClick={() => setActivePhase(phase.id)}
              >
                <Flex
                  w="12"
                  h="12"
                  rounded="full"
                  align="center"
                  justify="center"
                  transition="all 0.2s"
                  bg={activePhase === phase.id ? 'blue.500' : statusColor.bg}
                  color={activePhase === phase.id ? 'white' : statusColor.color}
                  _groupHover={{
                    transform: 'scale(1.1)',
                    bg: statusColor.hover
                  }}
                >
                  <Icon as={phase.id === 'validate' ? CheckCircle : phase.icon} boxSize="6" />
                </Flex>
                <Text
                  fontSize="sm"
                  fontWeight="medium"
                  mt="2"
                  color={activePhase === phase.id ? 'blue.500' : 'gray.600'}
                >
                  {phase.label}
                </Text>
                {phase.status === 'completed' && (
                  <Badge colorScheme="green" mt="1">
                    Completed
                  </Badge>
                )}
              </Flex>
              {index < phases.length - 1 && (
                <Box
                  h="px"
                  flex="1"
                  bg={phase.status === 'completed' ? 'green.400' : 'gray.200'}
                />
              )}
            </Flex>
          );
        })}
      </Flex>
    </Box>
  );
};

export default WorkflowStatus;