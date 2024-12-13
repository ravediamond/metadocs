import React, { useState, useEffect, useCallback, useContext } from 'react';
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
import { marked } from 'marked';

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

  const fetchResults = useCallback(async (phase) => {
    console.log('fetchResults called with phase:', phase);

    // Add a check for activePhase to prevent unnecessary calls
    if (!pipeline || !selectedVersion || phase !== state.activePhase) {
      console.log('Skipping fetchResults - conditions not met');
      return;
    }

    // Add check for existing results to prevent unnecessary refetching
    if (results[phase]?.content) {
      console.log('Results already exist for phase:', phase);
      return;
    }

    try {
      const versionIdMap = {
        'parse': pipeline.current_parse_id,
        'extract': pipeline.current_extract_id,
        'merge': pipeline.current_merge_id,
        'group': pipeline.current_group_id,
        'ontology': pipeline.current_ontology_id
      };

      const versionId = versionIdMap[phase];

      if (!versionId) {
        console.log('No version ID for phase:', phase);
        return;
      }

      const [metadata, content] = await Promise.all([
        processing[`get${phase.charAt(0).toUpperCase() + phase.slice(1)}Version`](
          currentTenant,
          domain_id,
          selectedVersion.pipeline_id,
          versionId,
          token
        ),
        processing.getProcessingContent(
          currentTenant,
          domain_id,
          selectedVersion.pipeline_id,
          phase,
          versionId,
          token
        )
      ]);

      setResults(prev => ({
        ...prev,
        [phase]: {
          ...metadata,
          content: content.content
        }
      }));

    } catch (error) {
      console.error('Error in fetchResults:', error);
      toast({
        title: `Error fetching ${phase} results`,
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  }, [pipeline, selectedVersion, currentTenant, domain_id, token, state.activePhase, results]);

  // Modify the pipeline effect to not trigger fetchResults directly
  const fetchPipeline = useCallback(async () => {
    if (!selectedVersion?.pipeline_id) return;

    try {
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );

      setPipeline(pipelineData);

      if (pipelineData.stage) {
        const newActivePhase = pipelineData.stage.toLowerCase();
        setState(prev => ({
          ...prev,
          activePhase: newActivePhase
        }));
      }

      updatePhaseStatuses(pipelineData.stage, pipelineData.status);
    } catch (error) {
      toast({
        title: 'Error fetching pipeline',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  }, [selectedVersion, currentTenant, domain_id, token]);

  // Modify the polling effect
  useEffect(() => {
    let interval;

    if (pipeline?.status === 'RUNNING') {
      interval = setInterval(() => {
        fetchPipeline();
      }, 5000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [pipeline?.status, fetchPipeline]);

  // Separate effect for fetching results when active phase changes
  useEffect(() => {
    if (!state.activePhase || !pipeline) return;

    // Only fetch if we don't have results for this phase yet
    if (!results[state.activePhase]?.content) {
      fetchResults(state.activePhase);
    }
  }, [state.activePhase, pipeline, fetchResults]);

  // Clear results when version changes
  useEffect(() => {
    setResults({
      parse: null,
      extract: null,
      merge: null,
      group: null,
      ontology: null
    });
  }, [selectedVersion]);

  // Fetch domain versions
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

  // Fetch domain files
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
  // Selected version effect
  useEffect(() => {
    console.log('Selected version changed:', selectedVersion);
    if (selectedVersion?.pipeline_id) {
      fetchPipeline();
    }
  }, [selectedVersion, fetchPipeline]);

  // Pipeline status change effect
  useEffect(() => {
    console.log('Pipeline status changed:', pipeline?.status);
    let interval;

    if (pipeline?.status === 'RUNNING') {
      interval = setInterval(() => {
        console.log('Polling: fetching pipeline and results');
        fetchPipeline();
        if (state.activePhase) {
          console.log('Polling: fetching results for phase:', state.activePhase);
          fetchResults(state.activePhase);
        }
      }, 5000);
    }

    return () => {
      if (interval) {
        console.log('Clearing polling interval');
        clearInterval(interval);
      }
    };
  }, [pipeline?.status, state.activePhase, fetchPipeline, fetchResults]);

  // Active phase change effect
  useEffect(() => {
    console.log('Active phase or pipeline changed:', {
      activePhase: state.activePhase,
      pipelineId: pipeline?.id
    });

    if (!state.activePhase || !pipeline) return;

    fetchResults(state.activePhase);
  }, [state.activePhase, pipeline, fetchResults]);

  // Clear results when version changes
  useEffect(() => {
    setResults({
      parse: null,
      extract: null,
      merge: null,
      group: null,
      ontology: null
    });
  }, [selectedVersion]);

  const updatePhaseStatuses = (currentStage, pipelineStatus) => {
    if (!currentStage) return phases;

    const stageOrder = ['PARSE', 'EXTRACT', 'MERGE', 'GROUP', 'ONTOLOGY', 'VALIDATE', 'COMPLETED'];
    const currentIndex = stageOrder.indexOf(currentStage);

    setState(prev => ({
      ...prev,
      activePhase: currentStage.toLowerCase()
    }));

    return phases.map((phase) => {
      const phaseIndex = stageOrder.indexOf(phase.id.toUpperCase());
      let status = 'pending';

      if (phaseIndex < currentIndex) {
        status = 'completed';
      } else if (phaseIndex === currentIndex) {
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
      fetchPipeline();
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
      fetchPipeline();
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
      fetchPipeline();
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
      fetchPipeline();
    } catch (error) {
      toast({
        title: 'Error completing pipeline',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const ResultsViewer = ({ phase, results }) => {
    const currentResults = results[phase];

    if (!currentResults) return null;

    return (
      <Box p={4} w="full" h="full" overflow="auto">
        {currentResults.content ? (
          phase === 'parse' ? (
            <div dangerouslySetInnerHTML={{ __html: marked(currentResults.content) }} />
          ) : (
            <pre>{currentResults.content}</pre>
          )
        ) : (
          <Text>No content available</Text>
        )}
      </Box>
    );
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