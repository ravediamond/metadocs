import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Flex, Text, useToast } from '@chakra-ui/react';
import { FileText, Network } from 'lucide-react';
import AuthContext from '../context/AuthContext';
import { files, processing, domains } from '../api/api';
import ChatPanel from '../components/chat/ChatPanel';
import WorkflowStatus from '../components/processing/WorkflowStatus';
import PhaseControls from '../components/processing/PhaseControls';
import DomainVersionControl from '../components/processing/DomainVersionControl';
import { ResizablePanel } from '../components/processing/ResizablePanel';


const ProcessingWorkspace = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const toast = useToast();
  const [domainVersion, setDomainVersion] = useState(null);

  const [state, setState] = useState({
    activePhase: 'parse',
    selectedFile: '',
    selectedParsedFile: '',
    selectedVersion: '',
    files: [],
    parsedFiles: [],
    versions: [],
    isLoading: true,
    domainConfig: null
  });

  const phases = [
    { id: 'parse', icon: FileText, label: 'Parse', status: 'completed' },
    { id: 'extract', icon: FileText, label: 'Extract', status: 'in_progress' },
    { id: 'merge', icon: Network, label: 'Merge', status: 'pending' },
    { id: 'group', icon: Network, label: 'Group', status: 'pending' },
    { id: 'ontology', icon: Network, label: 'Ontology', status: 'pending' }
  ];

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [filesData, configData] = await Promise.all([
          files.getAll(currentTenant, domain_id, token),
          domains.getById(currentTenant, domain_id, token)
        ]);

        console.log(configData);

        setState(prev => ({
          ...prev,
          files: filesData.map(file => ({
            value: file.id,
            label: file.name
          })),
          domainConfig: configData,
          isLoading: false
        }));
      } catch (error) {
        toast({
          title: 'Error fetching data',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    fetchInitialData();
  }, [currentTenant, domain_id, token]);

  const handleStartParse = async () => {
    try {
      await processing.startParse(
        currentTenant,
        domain_id,
        state.selectedVersion,
        state.selectedFile,
        token
      );
      
      toast({
        title: 'Parsing started',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      setState(prev => ({ ...prev, activePhase: 'extract' }));
    } catch (error) {
      toast({
        title: 'Error starting parse',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleStartExtract = async () => {
    try {
      await processing.startExtract(
        currentTenant,
        domain_id,
        state.selectedVersion,
        state.selectedParsedFile,
        token
      );
      
      toast({
        title: 'Extraction started',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      setState(prev => ({ ...prev, activePhase: 'merge' }));
    } catch (error) {
      toast({
        title: 'Error starting extraction',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  return (
    <Flex h="100vh" bg="gray.50">
      <Box flex="1" p="6">
        <DomainVersionControl
          domainId={domain_id}
          tenantId={currentTenant}
          token={token}
          domains={domains}
          onVersionChange={setDomainVersion}
        />
        <WorkflowStatus 
          phases={phases}
          activePhase={state.activePhase}
          setActivePhase={(phase) => setState(prev => ({ ...prev, activePhase: phase }))}
          currentWorkflowVersion={state.domainConfig?.version || '1.0.0'}
        />
        <Flex gap="4" mb="6">
         <PhaseControls
          {...state}
          domainVersion={state.domainVersion}
          handleStartParse={handleStartParse}
          handleStartExtract={handleStartExtract}
          setSelectedFile={(file) => setState(prev => ({ ...prev, selectedFile: file }))}
          setSelectedParsedFile={(file) => setState(prev => ({ ...prev, selectedParsedFile: file }))}
          setSelectedVersion={(version) => setState(prev => ({ ...prev, selectedVersion: version }))}
         />
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
            Visualization for {state.activePhase} phase
          </Text>
        </Flex>
      </Box>
      <ResizablePanel>
        <Box w="full" borderLeftWidth="1px">
          <ChatPanel />
        </Box>
      </ResizablePanel>
    </Flex>
  );
};

export default ProcessingWorkspace;