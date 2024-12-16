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
  const [pipeline, setPipeline] = useState(null);
  const [activeStage, setActiveStage] = useState('parse');
  const [results, setResults] = useState({});

  // Pipeline automation state
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);

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
    if (!selectedVersion?.pipeline_id || !isRunning) {
      console.log('🔍 Poll conditions not met:', {
        hasPipelineId: !!selectedVersion?.pipeline_id,
        isRunning,
        selectedVersion
      });
      return;
    }

    try {
      console.log('📡 Fetching pipeline data:', {
        pipelineId: selectedVersion.pipeline_id,
        tenant: currentTenant,
        domainId: domain_id
      });

      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );

      setPipeline(pipelineData);
      console.log('🔄 Pipeline Status:', {
        stage: pipelineData.stage,
        status: pipelineData.status,
        parseId: pipelineData.current_parse_id,
        extractId: pipelineData.current_extract_id,
        mergeId: pipelineData.current_merge_id,
        groupId: pipelineData.current_group_id,
        ontologyId: pipelineData.current_ontology_id
      });

      if (pipelineData.status === 'COMPLETED') {
        console.log('✅ Stage completed:', pipelineData.stage);

        try {
          switch (pipelineData.stage) {
            case 'PARSE':
              console.log('🚀 Starting Extract stage with:', {
                parseId: pipelineData.current_parse_id
              });
              if (pipelineData.current_parse_id) {
                await processing.startExtract(
                  currentTenant,
                  domain_id,
                  selectedVersion.version_number,
                  pipelineData.current_parse_id,
                  token
                );
                console.log('✨ Extract stage started successfully');
              } else {
                console.warn('⚠️ No parse ID available to start Extract stage');
              }
              break;

            case 'EXTRACT':
              console.log('🚀 Starting Merge stage with:', {
                extractId: pipelineData.current_extract_id
              });
              if (pipelineData.current_extract_id) {
                await processing.startMerge(
                  currentTenant,
                  domain_id,
                  selectedVersion.version_number,
                  { extract_version_ids: [pipelineData.current_extract_id] },
                  token
                );
                console.log('✨ Merge stage started successfully');
              } else {
                console.warn('⚠️ No extract ID available to start Merge stage');
              }
              break;

            case 'MERGE':
              console.log('🚀 Starting Group stage with:', {
                mergeId: pipelineData.current_merge_id
              });
              if (pipelineData.current_merge_id) {
                await processing.startGroup(
                  currentTenant,
                  domain_id,
                  selectedVersion.version_number,
                  pipelineData.current_merge_id,
                  token
                );
                console.log('✨ Group stage started successfully');
              } else {
                console.warn('⚠️ No merge ID available to start Group stage');
              }
              break;

            case 'GROUP':
              console.log('🚀 Starting Ontology stage with:', {
                mergeId: pipelineData.current_merge_id,
                groupId: pipelineData.current_group_id
              });
              if (pipelineData.current_merge_id && pipelineData.current_group_id) {
                await processing.startOntology(
                  currentTenant,
                  domain_id,
                  selectedVersion.version_number,
                  {
                    merge_version_id: pipelineData.current_merge_id,
                    group_version_id: pipelineData.current_group_id
                  },
                  token
                );
                console.log('✨ Ontology stage started successfully');
              } else {
                console.warn('⚠️ Missing IDs required to start Ontology stage');
              }
              break;

            case 'ONTOLOGY':
              console.log('🚀 Starting Validate stage');
              await processing.startValidate(
                currentTenant,
                domain_id,
                selectedVersion.version_number,
                token
              );
              console.log('✨ Validate stage started successfully');
              break;

            case 'VALIDATE':
              console.log('🎉 Pipeline validation completed, finalizing...');
              await processing.complete(
                currentTenant,
                domain_id,
                selectedVersion.version_number,
                token
              );
              setIsRunning(false);
              console.log('✨ Pipeline completed successfully');
              break;

            default:
              console.log('❓ Unknown stage:', pipelineData.stage);
          }
        } catch (error) {
          console.error('❌ Stage transition error:', {
            stage: pipelineData.stage,
            error: error.message,
            fullError: error
          });
          setError(`Failed to transition from ${pipelineData.stage}: ${error.message}`);
          setIsRunning(false);
        }
      } else if (pipelineData.status === 'FAILED') {
        console.error('❌ Pipeline failed:', {
          stage: pipelineData.stage,
          error: pipelineData.error,
          fullPipelineData: pipelineData
        });
        setIsRunning(false);
        setError(`Pipeline failed at stage ${pipelineData.stage}`);
      } else {
        console.log('⏳ Pipeline in progress:', {
          stage: pipelineData.stage,
          status: pipelineData.status,
          fullPipelineData: pipelineData
        });
      }

      // Fetch current stage results if available
      const currentVersionId = pipelineData[`current_${pipelineData.stage.toLowerCase()}_id`];
      if (currentVersionId) {
        console.log('📥 Fetching results for:', {
          stage: pipelineData.stage,
          versionId: currentVersionId
        });
        await fetchResults(pipelineData.stage.toLowerCase(), currentVersionId);
      }

    } catch (error) {
      console.error('❌ Pipeline polling error:', {
        error: error.message,
        fullError: error
      });
      setIsRunning(false);
      setError('Failed to get pipeline status');
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token, isRunning, fetchResults]);

  // Add logs to the polling setup
  useEffect(() => {
    console.log('🔄 Polling effect triggered:', { isRunning });
    if (isRunning) {
      console.log('🚀 Starting polling...');
      pollPipelineStatus();
      const interval = setInterval(pollPipelineStatus, 5000);
      return () => {
        console.log('🛑 Stopping polling...');
        clearInterval(interval);
      };
    }
  }, [isRunning, pollPipelineStatus]);

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

  useEffect(() => {
    console.log('Component mounted with:', {
      isRunning,
      selectedVersion,
      domainFiles: domainFiles?.length,
      pipeline
    });
  }, [isRunning, selectedVersion, domainFiles, pipeline]);

  // Start automated pipeline
  const startPipeline = async () => {
    if (!selectedVersion || !domainFiles.length) {
      console.log('Cannot start pipeline:', { selectedVersion, domainFilesLength: domainFiles.length });
      return;
    }

    console.log('Starting pipeline with:', {
      version: selectedVersion,
      files: domainFiles
    });

    setIsRunning(true);
    setError(null);

    try {
      // Start parsing for each file
      for (const file of domainFiles) {
        console.log('Starting parse for file:', file);
        const response = await processing.startParse(
          currentTenant,
          domain_id,
          selectedVersion.version_number,
          file.file_version_id,
          token
        );
        console.log('Parse started with response:', response);

        // Update selectedVersion with pipeline ID from response
        if (response.pipeline_id) {
          setSelectedVersion(prev => ({
            ...prev,
            pipeline_id: response.pipeline_id
          }));
          console.log('Updated selectedVersion with pipeline_id:', response.pipeline_id);
        }
      }

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
    if (!pipeline?.[`current_${stage}_id`]) return null;
    return results[stage];
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
            currentStage={pipeline?.stage}
            error={error}
            onStart={startPipeline}
            onStop={stopPipeline}
            isStartDisabled={!selectedVersion || domainFiles.length === 0}
          />

          <WorkflowStatus
            phases={phases}
            activePhase={activeStage}
            setActivePhase={setActiveStage}
            pipeline={pipeline}
            currentWorkflowVersion={selectedVersion?.version_number}
          />

          <StageDetailPanel
            stage={{
              id: activeStage,
              label: phases.find(p => p.id === activeStage)?.label,
              status: pipeline?.stage === activeStage.toUpperCase() ? pipeline.status : 'pending'
            }}
            files={domainFiles}
            results={getStageContent(activeStage)}
            isLoading={isRunning && pipeline?.stage === activeStage.toUpperCase()}
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