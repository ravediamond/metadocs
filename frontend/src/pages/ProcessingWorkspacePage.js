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

  const handleVersionChange = useCallback((newVersion) => {
    setResults({}); // Clear previous results
    setSelectedVersion(newVersion);
  }, []);

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
      console.log('[Results] Skipping fetch - missing pipeline or version ID', {
        pipelineId: selectedVersion?.pipeline_id,
        versionId
      });
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

      console.log(`[Results] Raw content for ${stage}:`, content);

      if (!content) {
        console.warn(`[Results] No content returned for stage ${stage}`);
        return;
      }

      // For ontology stage, parse the JSON content
      if (stage === 'ontology') {
        try {
          // Handle both string content and direct JSON objects
          const parsedContent = typeof content.content === 'string'
            ? JSON.parse(content.content)
            : content.content;

          console.log(`[Results] Parsed ontology content:`, parsedContent);

          setResults(prev => {
            const newResults = {
              ...prev,
              [stage]: parsedContent
            };
            console.log(`[Results] Updated results state for ${stage}:`, newResults);
            return newResults;
          });
        } catch (error) {
          console.error('[Results] Error parsing ontology content:', error, {
            content: content.content
          });
          setResults(prev => ({
            ...prev,
            [stage]: content.content // Fallback to raw content if parsing fails
          }));
        }
      } else {
        setResults(prev => {
          const newResults = {
            ...prev,
            [stage]: content.content
          };
          console.log(`[Results] Updated results state for ${stage}:`, newResults);
          return newResults;
        });
      }
      console.log(`[Results] Successfully fetched ${stage} results`);
    } catch (error) {
      console.error(`[Results] Error fetching ${stage} results:`, error);
      // Add the error to the results state to surface it in the UI
      setResults(prev => ({
        ...prev,
        [stage]: { error: error.message }
      }));
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token]);

  // Load pipeline data when version changes
  const loadPipelineData = useCallback(async () => {
    if (!selectedVersion?.pipeline_id) return;

    try {
      // Get pipeline status
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );

      if (!pipelineData) return;
      setPipeline(pipelineData);

      // Load results for all stages that have been completed
      const stagesInOrder = ['parse', 'extract', 'merge', 'group', 'ontology'];
      for (const stage of stagesInOrder) {
        const stageStatus = await processing.getStageStatus(
          currentTenant,
          domain_id,
          selectedVersion.pipeline_id,
          stage.toUpperCase(),
          token
        );

        if (stageStatus.latest_version_id) {
          await fetchResults(stage, stageStatus.latest_version_id);
        }
      }

      // If pipeline is completed, set active stage to ontology
      if (pipelineData.status === 'COMPLETED') {
        setActiveStage('ontology');
      } else if (pipelineData.stage) {
        // Otherwise set to current stage
        setActiveStage(pipelineData.stage.toLowerCase());
      }

    } catch (error) {
      console.error('[Init] Error loading pipeline data:', error);
      toast({
        title: 'Error loading pipeline data',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token, fetchResults, toast]);

  // Pipeline polling
  const pollPipelineStatus = useCallback(async () => {
    if (!isRunning || !selectedVersion?.pipeline_id) {
      return;
    }

    try {
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );

      if (!pipelineData) return;

      setPipeline(pipelineData);

      // Get all stage results up to current stage
      const stagesInOrder = ['parse', 'extract', 'merge', 'group', 'ontology'];
      const currentStageIndex = stagesInOrder.indexOf(pipelineData.stage.toLowerCase());

      // Fetch results for all stages up to current one
      for (let i = 0; i <= currentStageIndex; i++) {
        const stage = stagesInOrder[i];
        const stageStatus = await processing.getStageStatus(
          currentTenant,
          domain_id,
          selectedVersion.pipeline_id,
          stage.toUpperCase(),
          token
        );

        if (stageStatus.latest_version_id) {
          await fetchResults(stage, stageStatus.latest_version_id);
        }
      }

      // If pipeline completed, ensure we fetch all results
      if (pipelineData.status === 'COMPLETED') {
        for (const stage of stagesInOrder) {
          const stageStatus = await processing.getStageStatus(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            stage.toUpperCase(),
            token
          );

          if (stageStatus.latest_version_id) {
            await fetchResults(stage, stageStatus.latest_version_id);
          }
        }
        setActiveStage('ontology');
      }

      // Handle completion or failure
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
      console.error('[Polling] Error:', error);
      setError('Failed to update pipeline status');
      setIsRunning(false);
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token, isRunning, fetchResults, toast]);

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

  // Initial fetch of domain versions
  useEffect(() => {
    const fetchDomainVersions = async () => {
      setIsLoading(true);
      try {
        console.log('[Init] Fetching domain versions');
        const versions = await domains.getVersions(currentTenant, domain_id, token);
        setDomainVersions(versions);
        if (versions.length > 0) {
          handleVersionChange(versions[0]);
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
  }, [currentTenant, domain_id, token, toast, handleVersionChange]);

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

  // Load pipeline data when version changes
  useEffect(() => {
    if (selectedVersion?.pipeline_id) {
      loadPipelineData();
    }
  }, [selectedVersion?.pipeline_id, loadPipelineData]);

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

  if (isLoading) {
    return (
      <Flex h="100vh" bg="gray.50" justify="center" align="center">
        <Text>Loading...</Text>
      </Flex>
    );
  }

  const getStageContent = (stage) => {
    const content = results[stage];
    console.log(`Getting content for stage ${stage}:`, {
      content,
      allResults: results,
      hasContent: !!content,
      contentType: content ? typeof content : 'undefined'
    });

    if (content?.error) {
      console.error(`Error in stage ${stage}:`, content.error);
      return null;
    }

    // If it's the ontology stage and we have a nested ontology property, return that
    if (stage === 'ontology' && content?.ontology) {
      return content.ontology;
    }

    return content || null;
  };

  return (
    <Flex h="100vh" bg="gray.50">
      <Box flex="1" p="6">
        <VStack spacing={6} align="stretch">
          <DomainVersionControl
            versions={domainVersions}
            selectedVersion={selectedVersion}
            onVersionChange={handleVersionChange}
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