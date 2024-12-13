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

  const [results, setResults] = useState({
    parse: null,
    extract: null,
    merge: null,
    group: null,
    ontology: null
  });

  const fetchResults = async (phase) => {
    if (!pipeline || !selectedVersion) return;
    try {
      let result;
      switch (phase) {
        case 'parse':
          result = await processing.getParseVersion(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            pipeline.current_parse_id,
            token
          );
          break;
        case 'extract':
          result = await processing.getExtractVersion(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            pipeline.current_extract_id,
            token
          );
          break;
        case 'merge':
          result = await processing.getMergeVersion(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            pipeline.current_merge_id,
            token
          );
          break;
        case 'group':
          result = await processing.getGroupVersion(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            pipeline.current_group_id,
            token
          );
          break;
        case 'ontology':
          result = await processing.getOntologyVersion(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            pipeline.current_ontology_id,
            token
          );
          break;
      }
      setResults(prev => ({
        ...prev,
        [phase]: result
      }));
    } catch (error) {
      toast({
        title: `Error fetching ${phase} results`,
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  useEffect(() => {
    if (state.activePhase && pipeline?.status !== 'NOT_STARTED') {
      fetchResults(state.activePhase);
    }
  }, [state.activePhase, pipeline]);

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

  const updatePhaseStatuses = (currentStage, pipelineStatus) => {
    if (!currentStage) return phases;

    const stageOrder = ['PARSE', 'EXTRACT', 'MERGE', 'GROUP', 'ONTOLOGY', 'VALIDATE', 'COMPLETED'];
    const currentIndex = stageOrder.indexOf(currentStage);

    // Update the active phase based on the current stage
    setState(prev => ({
      ...prev,
      activePhase: currentStage.toLowerCase()
    }));

    const updatedPhases = phases.map((phase) => {
      const phaseIndex = stageOrder.indexOf(phase.id.toUpperCase());
      let status = 'pending';

      if (phaseIndex < currentIndex) {
        status = 'completed';
      } else if (phaseIndex === currentIndex) {
        // For the current phase, use the pipeline status to determine the status
        switch (pipelineStatus) {
          case 'RUNNING':
            status = 'in_progress';
            break;
          case 'COMPLETED':
            status = 'completed';
            break;
          case 'FAILED':
            status = 'error';
            break;
          case 'NOT_STARTED':
            status = 'pending';
            break;
          default:
            status = 'pending';
        }
      }

      return {
        ...phase,
        status
      };
    });

    return updatedPhases;
  };

  const fetchPipeline = async () => {
    if (!selectedVersion?.pipeline_id) return;
    try {
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );
      console.log(pipelineData);
      setPipeline(pipelineData);
      if (pipelineData.stage) {
        updatePhaseStatuses(pipelineData.stage, pipelineData.status);
      }
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

  useEffect(() => {
    let interval;
    if (pipeline?.status === 'RUNNING') {
      interval = setInterval(() => {
        fetchPipeline();
        if (state.activePhase) {
          fetchResults(state.activePhase);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [pipeline?.status, state.activePhase]);

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

  const ResultsViewer = ({ phase, results }) => {
    if (!results) return null;

    return (
      <Box p={4} w="full" h="full" overflow="auto">
        {phase === 'parse' && (
          <pre>{results.parse?.output_content || JSON.stringify(results.parse, null, 2)}</pre>
        )}
        {phase === 'extract' && (
          <pre>{JSON.stringify(results.extract?.entities || results.extract, null, 2)}</pre>
        )}
        {phase === 'merge' && (
          <pre>{JSON.stringify(results.merge?.merged_entities || results.merge, null, 2)}</pre>
        )}
        {phase === 'group' && (
          <pre>{JSON.stringify(results.group?.entity_groups || results.group, null, 2)}</pre>
        )}
        {phase === 'ontology' && (
          <pre>{JSON.stringify(results.ontology?.ontology || results.ontology, null, 2)}</pre>
        )}
      </Box>
    );
  };

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
          {results[state.activePhase] ? (
            <ResultsViewer
              phase={state.activePhase}
              results={results}
            />
          ) : (
            <Text color="gray.400">
              No results available for {state.activePhase} phase
            </Text>
          )}
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