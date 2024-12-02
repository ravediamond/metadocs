import React, { useState } from 'react';
import {
  Box,
  Button,
  Flex,
  Heading,
  Icon,
  Input,
  Select,
  Text,
  useColorModeValue
} from '@chakra-ui/react';
import { MessageSquare, FileText, Network, Settings, GitCommit } from 'lucide-react';

const SelectBox = ({ label, options, value, onChange }) => (
  <Box mb="4">
    <Text fontSize="sm" fontWeight="medium" color="gray.700" mb="1">
      {label}
    </Text>
    <Select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      bg="white"
      p="2"
      focusBorderColor="blue.500"
    >
      <option value="">Select {label.toLowerCase()}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </Select>
  </Box>
);

const WorkflowStatus = ({ phases, activePhase, setActivePhase, currentWorkflowVersion }) => {
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
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
        {phases.map((phase, index) => (
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
                bg={
                  activePhase === phase.id ? 'blue.500' :
                  phase.status === 'completed' ? 'green.100' :
                  phase.status === 'in_progress' ? 'blue.100' :
                  'gray.100'
                }
                color={
                  activePhase === phase.id ? 'white' :
                  phase.status === 'completed' ? 'green.600' :
                  phase.status === 'in_progress' ? 'blue.600' :
                  'gray.400'
                }
                _groupHover={{
                  transform: 'scale(1.1)',
                  bg: phase.status === 'completed' ? 'green.200' :
                      phase.status === 'in_progress' ? 'blue.200' :
                      'gray.200'
                }}
              >
                <Icon as={phase.icon} boxSize="6" />
              </Flex>
              <Text
                fontSize="sm"
                fontWeight="medium"
                mt="2"
                color={activePhase === phase.id ? 'blue.500' : 'gray.600'}
              >
                {phase.label}
              </Text>
            </Flex>
            {index < phases.length - 1 && (
              <Box
                h="px"
                flex="1"
                bg={phase.status === 'completed' ? 'green.400' : 'gray.200'}
              />
            )}
          </Flex>
        ))}
      </Flex>
    </Box>
  );
};

const KnowledgeGraphInterface = () => {
  const [activePhase, setActivePhase] = useState('parse');
  const [selectedFile, setSelectedFile] = useState('');
  const [selectedParsedFile, setSelectedParsedFile] = useState('');
  const [selectedVersion, setSelectedVersion] = useState('');

  const phases = [
    { id: 'parse', icon: FileText, label: 'Parse', status: 'completed' },
    { id: 'extract', icon: FileText, label: 'Extract', status: 'in_progress' },
    { id: 'merge', icon: Network, label: 'Merge', status: 'pending' },
    { id: 'group', icon: Network, label: 'Group', status: 'pending' },
    { id: 'ontology', icon: Network, label: 'Ontology', status: 'pending' }
  ];

  const files = [
    { value: 'doc1', label: 'document1.md' },
    { value: 'doc2', label: 'document2.md' },
    { value: 'doc3', label: 'document3.md' }
  ];

  const parsedFiles = [
    { value: 'parsed1', label: 'Parsed document1.md' },
    { value: 'parsed2', label: 'Parsed document2.md' },
    { value: 'parsed3', label: 'Parsed document3.md' }
  ];

  const versions = [
    { value: 'v1', label: 'Version 1 (2 mins ago)' },
    { value: 'v2', label: 'Version 2 (10 mins ago)' },
    { value: 'v3', label: 'Version 3 (15 mins ago)' }
  ];

  const renderSelectors = () => {
    switch(activePhase) {
      case 'parse':
        return (
          <>
            <Box w="64">
              <SelectBox
                label="Select File"
                options={files}
                value={selectedFile}
                onChange={setSelectedFile}
              />
            </Box>
            <Box w="64">
              <SelectBox
                label="Version"
                options={versions}
                value={selectedVersion}
                onChange={setSelectedVersion}
              />
            </Box>
          </>
        );
      case 'extract':
        return (
          <>
            <Box w="64">
              <SelectBox
                label="Select Parsed File"
                options={parsedFiles}
                value={selectedParsedFile}
                onChange={setSelectedParsedFile}
              />
            </Box>
            <Box w="64">
              <SelectBox
                label="Version"
                options={versions}
                value={selectedVersion}
                onChange={setSelectedVersion}
              />
            </Box>
          </>
        );
      default:
        return (
          <Box w="64">
            <SelectBox
              label="Version"
              options={versions}
              value={selectedVersion}
              onChange={setSelectedVersion}
            />
          </Box>
        );
    }
  };

  return (
    <Flex h="100vh" bg="gray.50">
      {/* Main content area */}
      <Box flex="1" p="6">
        <WorkflowStatus 
          phases={phases}
          activePhase={activePhase}
          setActivePhase={setActivePhase}
          currentWorkflowVersion="1.0.2"
        />
        <Flex gap="4" mb="6">
          {renderSelectors()}
        </Flex>
        <Flex
          h="calc(100% - 16rem)"
          bg="white"
          rounded="lg"
          shadow="sm"
          borderWidth="1px"
          align="center"
          justify="center"
        >
          <Text color="gray.400">
            Visualization for {activePhase} phase
          </Text>
        </Flex>
      </Box>

      {/* Right panel - chat interface */}
      <Flex w="96" bg="white" borderLeftWidth="1px" direction="column">
        <Flex p="4" borderBottomWidth="1px" align="center" justify="space-between">
          <Flex align="center" gap="2">
            <Icon as={MessageSquare} boxSize="5" color="blue.500" />
            <Text fontWeight="medium">Knowledge Assistant</Text>
          </Flex>
          <Icon
            as={Settings}
            boxSize="5"
            color="gray.400"
            cursor="pointer"
            _hover={{ color: 'gray.600' }}
          />
        </Flex>

        <Box flex="1" overflowY="auto" p="4" spacing="4">
          <Box bg="blue.50" rounded="lg" p="3" ml="8">
            <Text fontSize="sm">
              I can help you with:
              - Creating new versions
              - Modifying prompts
              - Analyzing results
              - Starting next phases
              
              What would you like to do?
            </Text>
          </Box>
        </Box>

        <Box p="4" borderTopWidth="1px">
          <Flex gap="2">
            <Input
              placeholder="Type your message..."
              p="3"
              focusBorderColor="blue.500"
            />
            <Button colorScheme="blue">
              Send
            </Button>
          </Flex>
        </Box>
      </Flex>
    </Flex>
  );
};

export default KnowledgeGraphInterface;