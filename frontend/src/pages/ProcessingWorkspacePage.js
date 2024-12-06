import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Flex, Text, useToast } from '@chakra-ui/react';
import { FileText, Network, CheckCircle } from 'lucide-react';
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
  const [domainVersions, setDomainVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [domainFiles, setDomainFiles] = useState([]);
  const [pipeline, setPipeline] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const [state, setState] = useState({
    activePhase: 'parse',
    selectedFile: '',
    selectedParsedFile: ''
  });

  const phases = [
    { id: 'parse', icon: FileText, label: 'Parse', status: 'pending' },
    { id: 'extract', icon: FileText, label: 'Extract', status: 'pending' },
    { id: 'merge', icon: Network, label: 'Merge', status: 'pending' },
    { id: 'group', icon: Network, label: 'Group', status: 'pending' },
    { id: 'ontology', icon: Network, label: 'Ontology', status: 'pending' },
    { id: 'validate', icon: CheckCircle, label: 'Validate', status: 'pending' }
  ];

  useEffect(() => {
    const fetchDomainFiles = async () => {
        if (!selectedVersion) return;
        
        try {
          const files = await domains.getDomainVersionFiles(
            currentTenant,
            domain_id,
            selectedVersion.version_number,
            token,
          );

          const mappedFiles = files.map(file => ({
            value: file.file_version_id,
            label: file.filename
          }));

          console.log("Mapped files:", mappedFiles);
          
          setDomainFiles(mappedFiles);
        } catch (error) {
          toast({
            title: 'Error fetching domain files',
            description: error.message,
            status: 'error',
            duration: 5000,
          });
        }
      };

    fetchDomainFiles();
  }, [selectedVersion, currentTenant, domain_id, token]);

  useEffect(() => {
    const fetchDomainVersions = async () => {
      setIsLoading(true);
      try {
        const versions = await domains.getVersions(currentTenant, domain_id, token);
        setDomainVersions(versions);
        if (versions.length > 0) {
          setSelectedVersion(versions[0]);
        }
      } catch (error) {
        toast({
          title: 'Error fetching versions',
          description: error.message,
          status: 'error',
          duration: 5000,
        });
      }
      setIsLoading(false);
    };

    fetchDomainVersions();
  }, [currentTenant, domain_id, token]);

  const fetchPipeline = async () => {
    if (!selectedVersion?.pipeline_id) return;
    try {
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );
      setPipeline(pipelineData);
      updatePhaseStatuses(pipelineData.stage);
    } catch (error) {
      toast({
        title: 'Error fetching pipeline',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  useEffect(() => {
    if (selectedVersion?.pipeline_id) {
      fetchPipeline();
    }
  }, [selectedVersion]);

  const updatePhaseStatuses = (currentStage) => {
    const stageOrder = ['PARSE', 'EXTRACT', 'MERGE', 'GROUP', 'ONTOLOGY', 'VALIDATE', 'COMPLETED'];
    const currentIndex = stageOrder.indexOf(currentStage);

    setState(prev => ({ ...prev, activePhase: currentStage.toLowerCase() }));

    const updatedPhases = phases.map((phase, index) => {
      const phaseIndex = stageOrder.indexOf(phase.id.toUpperCase());
      return {
        ...phase,
        status: phaseIndex < currentIndex ? 'completed' :
                phaseIndex === currentIndex ? 'in_progress' : 'pending'
      };
    });

    return updatedPhases;
  };

  const handleStartParse = async () => {
    try {
      await processing.startParse(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        state.selectedFile,
        token
      );
      toast({
        title: 'Parse process started',
        status: 'success',
        duration: 3000,
      });
      await fetchPipeline();
    } catch (error) {
      toast({
        title: 'Error starting parse',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleStartExtract = async () => {
    try {
      await processing.startExtract(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        state.selectedParsedFile,
        token
      );
      toast({
        title: 'Extract process started',
        status: 'success',
        duration: 3000,
      });
      await fetchPipeline();
    } catch (error) {
      toast({
        title: 'Error starting extract',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleStartValidate = async () => {
    try {
      await processing.startValidate(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        token
      );
      toast({
        title: 'Validation started',
        status: 'success',
        duration: 3000,
      });
      await fetchPipeline();
    } catch (error) {
      toast({
        title: 'Error starting validation',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleComplete = async () => {
    try {
      await processing.complete(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        token
      );
      toast({
        title: 'Pipeline completed',
        status: 'success',
        duration: 3000,
      });
      await fetchPipeline();
    } catch (error) {
      toast({
        title: 'Error completing pipeline',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  if (isLoading) {
    return (
      <Flex h="100vh" bg="gray.50" justify="center" align="center">
        <Text>Loading...</Text>
      </Flex>
    );
  }

  if (domainVersions.length === 0) {
    return (
      <Flex h="100vh" bg="gray.50" justify="center" align="center">
        <Text fontSize="xl">Please create a domain version to start processing</Text>
      </Flex>
    );
  }

  return (
    <Flex h="100vh" bg="gray.50">
      <Box flex="1" p="6">
        <DomainVersionControl
          versions={domainVersions}
          selectedVersion={selectedVersion}
          onVersionChange={setSelectedVersion}
        />
        <WorkflowStatus 
          phases={phases}
          activePhase={state.activePhase}
          pipeline={pipeline}
          currentWorkflowVersion={selectedVersion?.version_number}
        />
        <Flex gap="4" mb="6">
          <PhaseControls
            {...state}
            pipeline={pipeline}
            files={domainFiles}
            handleStartParse={handleStartParse}
            handleStartExtract={handleStartExtract}
            handleStartValidate={handleStartValidate}
            handleComplete={handleComplete}
            setSelectedFile={(file) => setState(prev => ({ ...prev, selectedFile: file }))}
            setSelectedParsedFile={(file) => setState(prev => ({ ...prev, selectedParsedFile: file }))}
            isLoading={isLoading}
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