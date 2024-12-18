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
    if (!selectedVersion?.pipeline_id || !versionId) return;

    try {
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
    } catch (error) {
      console.error(`Error fetching ${stage} results:`, error);
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token]);

  // Pipeline status polling
  const pollPipelineStatus = useCallback(async () => {
    if (!isRunning || !selectedVersion?.pipeline_id) return;

    try {
      // Get pipeline status
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );
      setPipeline(pipelineData);

      // Get stage status
      const stageStatus = await processing.getStageStatus(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        pipelineData.stage,
        token
      );

      // Fetch results if there's a latest version
      if (stageStatus.latest_version_id) {
        await fetchResults(pipelineData.stage.toLowerCase(), stageStatus.latest_version_id);
      }

      // Check if we can start next stage
      const stageDeps = await processing.getStageDependencies(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        pipelineData.stage,
        token
      );

      if (stageDeps.can_start && stageStatus.status === 'COMPLETED') {
        startNextStage(pipelineData.stage, stageStatus);
      }

    } catch (error) {
      console.error('Pipeline polling error:', error);
      setError('Failed to update pipeline status');
      setIsRunning(false);
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token, isRunning]);

  // Function to start next stage
  const startNextStage = async (currentStage, stageStatus) => {
    try {
      switch (currentStage) {
        case 'PARSE':
          // For each completed parse, start its corresponding extract
          const completedParses = stageStatus.versions.filter(v => v.status === "completed");
          console.log(`Found ${completedParses.length} completed parse versions:`,
            completedParses.map(v => v.version_id));

          // Check if extract is already running for these parse versions
          for (const parseVersion of completedParses) {
            // Get existing extract versions
            const existingExtracts = await processing.getStageVersions(
              currentTenant,
              domain_id,
              selectedVersion.pipeline_id,
              'EXTRACT',
              token
            );

            const hasExtract = existingExtracts.some(
              e => e.input_version_ids?.includes(parseVersion.version_id)
            );

            console.log(`Parse version ${parseVersion.version_id}:`, {
              hasExistingExtract: hasExtract,
              parseStatus: parseVersion.status
            });

            // Only start extract if one doesn't exist for this parse
            if (!hasExtract) {
              console.log(`Starting new extract for parse version ${parseVersion.version_id}`);
              await processing.startStageBatch(
                currentTenant,
                domain_id,
                selectedVersion.pipeline_id,
                'EXTRACT',
                [parseVersion.version_id], // Single parse version instead of all
                token
              );
            } else {
              console.log(`Extract already exists for parse version ${parseVersion.version_id}, skipping`);
            }
          }
          break;

        case 'EXTRACT':
          // Once all extracts are complete, start merge
          const extractVersions = stageStatus.versions
            .filter(v => v.status === "completed")
            .map(v => v.version_id);

          console.log('Completed extract versions:', extractVersions);

          // Check if all files have been extracted (compare with parse versions)
          const parseVersions = await processing.getStageVersions(
            currentTenant,
            domain_id,
            selectedVersion.pipeline_id,
            'PARSE',
            token
          );

          const completedParseCount = parseVersions.filter(v => v.status === "completed").length;

          console.log('Pipeline status:', {
            completedExtractCount: extractVersions.length,
            completedParseCount,
            readyForMerge: extractVersions.length === completedParseCount
          });

          // Only start merge when all files have been extracted
          if (extractVersions.length === completedParseCount) {
            console.log('Starting merge with extract versions:', extractVersions);
            await processing.startMerge(
              currentTenant,
              domain_id,
              selectedVersion.version_number,
              { extract_version_ids: extractVersions },
              token
            );
          }
          break;

        case 'MERGE':
          console.log('Merge status:', {
            latestVersionId: stageStatus.latest_version_id,
            status: stageStatus.status
          });
          // Start group only when merge is complete
          if (stageStatus.latest_version_id) {
            console.log('Starting group for merge version:', stageStatus.latest_version_id);
            await processing.startGroup(
              currentTenant,
              domain_id,
              selectedVersion.version_number,
              stageStatus.latest_version_id,
              token
            );
          }
          break;

        case 'GROUP':
          console.log('Group status:', {
            groupVersionId: stageStatus.latest_version_id,
            mergeVersionId: pipeline.latest_merge_version_id,
            status: stageStatus.status
          });
          // Start ontology only when both merge and group are complete
          if (stageStatus.latest_version_id && pipeline.latest_merge_version_id) {
            console.log('Starting ontology with versions:', {
              mergeVersionId: pipeline.latest_merge_version_id,
              groupVersionId: stageStatus.latest_version_id
            });
            await processing.startOntology(
              currentTenant,
              domain_id,
              selectedVersion.version_number,
              {
                merge_version_id: pipeline.latest_merge_version_id,
                group_version_id: stageStatus.latest_version_id
              },
              token
            );
          }
          break;

        default:
          break;
      }
    } catch (error) {
      console.error('Error starting next stage:', error);
      setError(`Failed to start next stage after ${currentStage}`);
    }
  };

  // Start pipeline function
  const startPipeline = async () => {
    if (!selectedVersion || !domainFiles.length) {
      console.log('Cannot start pipeline:', { selectedVersion, domainFilesLength: domainFiles.length });
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      // Start parse for each file
      await processing.startStageBatch(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        'PARSE',
        domainFiles.map(file => file.file_version_id),
        token
      );

      toast({
        title: 'Pipeline started',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Error starting pipeline:', error);
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

  // Set up polling
  useEffect(() => {
    if (isRunning) {
      console.log('Starting polling...');
      pollPipelineStatus();
      const interval = setInterval(pollPipelineStatus, 5000);
      return () => {
        console.log('Stopping polling...');
        clearInterval(interval);
      };
    }
  }, [isRunning, pollPipelineStatus]);

  // Stop pipeline
  const stopPipeline = async () => {
    setIsRunning(false);
  };

  // Initial fetch of domain versions
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

  // Fetch domain files when version changes
  useEffect(() => {
    const fetchDomainFiles = async () => {
      if (!selectedVersion) return;
      try {
        const files = await domains.getDomainVersionFiles(
          currentTenant,
          domain_id,
          selectedVersion.version_number,
          token
        );
        setDomainFiles(files);
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

  const getCurrentPhaseStatus = () => {
    if (!pipeline) return 'pending';
    return pipeline.status;
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