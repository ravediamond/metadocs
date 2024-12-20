import React, { useState, useEffect, useContext, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Flex, useToast, VStack, Text } from '@chakra-ui/react';
import { processing, domains } from '../api/api';
import AuthContext from '../context/AuthContext';
import ChatPanel from '../components/chat/ChatPanel';
import WorkflowStatus from '../components/processing/WorkflowStatus';
import DomainVersionControl from '../components/processing/DomainVersionControl';
import { ResizablePanel } from '../components/processing/ResizablePanel';
import StageDetailPanel from '../components/processing/StageDetailPanel';
import ProcessingControls from '../components/processing/ProcessingControls';

const ProcessingWorkspace = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const toast = useToast();

  // Basic state
  const [isLoading, setIsLoading] = useState(true);
  const [domainVersions, setDomainVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [domainFiles, setDomainFiles] = useState([]);
  const [activeStage, setActiveStage] = useState('parse');
  const [results, setResults] = useState({});

  // Pipeline state
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const [pipeline, setPipeline] = useState(null);

  const phases = [
    { id: 'parse', label: 'Parse', status: 'pending' },
    { id: 'extract', label: 'Extract', status: 'pending' },
    { id: 'merge', label: 'Merge', status: 'pending' },
    { id: 'group', label: 'Group', status: 'pending' },
    { id: 'ontology', label: 'Ontology', status: 'pending' },
    { id: 'validate', label: 'Validate', status: 'pending' }
  ];

  // Fetch results for a specific stage
  const fetchResults = useCallback(async (stage, versionId) => {
    if (!selectedVersion?.pipeline_id || !versionId) {
      console.log('[Results] Skipping fetch - missing pipeline or version ID');
      return;
    }

    try {
      console.log(`[Results] Fetching ${stage} results for version ${versionId}`);
      const content = await processing.getProcessingContent(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        stage,
        versionId,
        token
      );

      setResults(prev => ({
        ...prev,
        [stage]: content.content
      }));
      console.log(`[Results] Successfully fetched ${stage} results`);
    } catch (error) {
      console.error(`[Results] Error fetching ${stage} results:`, error);
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token]);

  // Pipeline polling
  const pollPipelineStatus = useCallback(async () => {
    if (!isRunning || !selectedVersion?.pipeline_id) {
      console.log('[Polling] Skipping poll - pipeline not running or no selected version');
      return;
    }

    try {
      console.log('[Polling] Fetching pipeline status...');

      // Get pipeline status
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );

      if (!pipelineData) {
        console.log('[Polling] No pipeline data received');
        return;
      }

      // Update pipeline state
      setPipeline(pipelineData);

      // Get current stage status
      const stageStatus = await processing.getStageStatus(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        pipelineData.stage,
        token
      );

      // Only fetch results if stage has a latest version and pipeline is still running
      if (stageStatus.latest_version_id && pipelineData.status !== 'COMPLETED') {
        await fetchResults(pipelineData.stage.toLowerCase(), stageStatus.latest_version_id);
      }

      // Stop polling if pipeline is completed or failed
      if (['COMPLETED', 'FAILED'].includes(pipelineData.status)) {
        setIsRunning(false);
        if (pipelineData.status === 'FAILED') {
          setError(pipelineData.error || 'Pipeline processing failed');
          toast({
            title: 'Pipeline Failed',
            description: pipelineData.error || 'Pipeline processing failed',
            status: 'error',
            duration: 5000,
          });
        } else {
          toast({
            title: 'Pipeline Completed',
            status: 'success',
            duration: 3000,
          });
        }
      }

    } catch (error) {
      console.error('[Polling] Error in pipeline polling:', error);
      setError('Failed to update pipeline status');
      setIsRunning(false);
    }
  }, [
    currentTenant,
    domain_id,
    selectedVersion?.pipeline_id,
    token,
    isRunning,
    fetchResults,
    toast
  ]);

  // Set up polling
  useEffect(() => {
    let intervalId;
    if (isRunning) {
      console.log('[Polling] Starting polling cycle...');
      pollPipelineStatus(); // Initial poll
      intervalId = setInterval(pollPipelineStatus, 5000);
    }
    return () => {
      if (intervalId) {
        console.log('[Polling] Stopping polling...');
        clearInterval(intervalId);
      }
    };
  }, [isRunning, pollPipelineStatus]);

  // Start pipeline
  const startPipeline = async () => {
    if (!selectedVersion || !domainFiles.length) {
      console.log('[Pipeline Start] Cannot start pipeline:', {
        selectedVersion,
        domainFilesLength: domainFiles.length
      });
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      console.log('[Pipeline Start] Starting pipeline processing');

      await processing.startPipeline(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        token
      );

      toast({
        title: 'Pipeline started',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('[Pipeline Start] Error:', error);
      setIsRunning(false);
      setError('Failed to start pipeline');
      toast({
        title: 'Error starting pipeline',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  // Stop pipeline
  const stopPipeline = async () => {
    try {
      console.log('[Pipeline Stop] Stopping pipeline');

      await processing.stopPipeline(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        token
      );

      setIsRunning(false);
      toast({
        title: 'Pipeline stopped',
        status: 'info',
        duration: 3000,
      });
    } catch (error) {
      console.error('[Pipeline Stop] Error:', error);
      toast({
        title: 'Error stopping pipeline',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  // Initial fetch of domain versions
  useEffect(() => {
    const fetchDomainVersions = async () => {
      setIsLoading(true);
      try {
        console.log('[Init] Fetching domain versions');
        const versions = await domains.getVersions(currentTenant, domain_id, token);
        setDomainVersions(versions);
        if (versions.length > 0) {
          setSelectedVersion(versions[0]);
        }
        console.log('[Init] Domain versions loaded:', versions.length);
      } catch (error) {
        console.error('[Init] Error fetching versions:', error);
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
  }, [currentTenant, domain_id, token, toast]);

  // Fetch domain files when version changes
  useEffect(() => {
    const fetchDomainFiles = async () => {
      if (!selectedVersion) return;
      try {
        console.log('[Init] Fetching domain files for version:', selectedVersion.version_number);
        const files = await domains.getDomainVersionFiles(
          currentTenant,
          domain_id,
          selectedVersion.version_number,
          token
        );
        setDomainFiles(files);
        console.log('[Init] Domain files loaded:', files.length);
      } catch (error) {
        console.error('[Init] Error fetching domain files:', error);
        toast({
          title: 'Error fetching domain files',
          description: error.message,
          status: 'error',
          duration: 5000,
        });
      }
    };
    fetchDomainFiles();
  }, [selectedVersion, currentTenant, domain_id, token, toast]);

  if (isLoading) {
    return (
      <Flex h="100vh" bg="gray.50" justify="center" align="center">
        <Text>Loading...</Text>
      </Flex>
    );
  }

  const getStageContent = (stage) => {
    return results[stage] || null;
  };

  return (
    <Flex h="100vh" bg="gray.50">
      <Box flex="1" p="6">
        <VStack spacing={6} align="stretch">
          <DomainVersionControl
            versions={domainVersions}
            selectedVersion={selectedVersion}
            onVersionChange={setSelectedVersion}
          />

          <ProcessingControls
            isRunning={isRunning}
            currentStage={activeStage.toUpperCase()}
            error={error}
            onStart={startPipeline}
            onStop={stopPipeline}
            isStartDisabled={!selectedVersion || domainFiles.length === 0}
          />

          <WorkflowStatus
            phases={phases}
            activePhase={activeStage}
            setActivePhase={setActiveStage}
            currentStatus={pipeline?.status || 'pending'}
            currentWorkflowVersion={selectedVersion?.version_number}
          />

          <StageDetailPanel
            stage={{
              id: activeStage,
              label: phases.find(p => p.id === activeStage)?.label,
              status: pipeline?.status || 'pending'
            }}
            files={domainFiles}
            results={getStageContent(activeStage)}
            isLoading={isRunning}
          />
        </VStack>
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