import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Flex, useToast, VStack, IconButton, Text } from '@chakra-ui/react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { processing, domains } from '../api/api';
import ChatPanel from '../components/chat/ChatPanel';
import DomainVersionControl from '../components/processing/DomainVersionControl';
import ProcessingControls from '../components/processing/ProcessingControls';
import ProcessingStatusPanel from '../components/processing/ProcessingStatusPanel';

const ProcessingWorkspace = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useAuth();
  const toast = useToast();

  // Basic state
  const [isLoading, setIsLoading] = useState(true);
  const [domainVersions, setDomainVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [domainFiles, setDomainFiles] = useState([]);

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [processingResults, setProcessingResults] = useState({});
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [visualization, setVisualization] = useState({
    type: 'none',
    content: null,
    title: null
  });

  const handleVersionChange = useCallback((newVersion) => {
    setProcessingResults({});
    setSelectedVersion(newVersion);
  }, []);

  const handleVisualizationUpdate = useCallback((vizData) => {
    console.log('Setting visualization:', vizData);
    setVisualization(vizData);
  }, []);

  // Poll pipeline status
  const pollPipelineStatus = useCallback(async () => {
    if (!isProcessing || !selectedVersion?.pipeline_id) return;

    try {
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );

      setPipeline(pipelineData);

      if (pipelineData.results) {
        setProcessingResults(pipelineData.results);
      }

      if (['COMPLETED', 'FAILED'].includes(pipelineData.status)) {
        setIsProcessing(false);
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
      setIsProcessing(false);
    }
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token, isProcessing, toast]);

  // Load pipeline data
  const loadPipelineData = useCallback(async () => {
    if (!selectedVersion?.pipeline_id) return;
    try {
      const pipelineData = await processing.getPipeline(
        currentTenant,
        domain_id,
        selectedVersion.pipeline_id,
        token
      );
      setPipeline(pipelineData);
      if (pipelineData.results) {
        setProcessingResults(pipelineData.results);
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
  }, [currentTenant, domain_id, selectedVersion?.pipeline_id, token, toast]);

  // Start pipeline
  const startPipeline = async () => {
    if (!selectedVersion || !domainFiles.length) return;

    setIsProcessing(true);
    setError(null);

    try {
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
      setIsProcessing(false);
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
      await processing.stopPipeline(
        currentTenant,
        domain_id,
        selectedVersion.version_number,
        token
      );
      setIsProcessing(false);
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

  // Set up polling
  useEffect(() => {
    let intervalId;
    if (isProcessing) {
      pollPipelineStatus(); // Initial poll
      intervalId = setInterval(pollPipelineStatus, 5000);
    }
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isProcessing, pollPipelineStatus]);

  // Load initial data
  useEffect(() => {
    const fetchDomainVersions = async () => {
      setIsLoading(true);
      try {
        const versions = await domains.getVersions(currentTenant, domain_id, token);
        setDomainVersions(versions);
        if (versions.length > 0) {
          handleVersionChange(versions[0]);
        }
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

  // Load domain files
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

  if (isLoading) {
    return (
      <Flex h="100vh" bg="gray.50" justify="center" align="center">
        <Text>Loading...</Text>
      </Flex>
    );
  }

  return (
    <Box h="100vh" bg="gray.50">
      <Box p="6">
        {/* Top Controls */}
        <VStack spacing={6} align="stretch" mb="6">
          <DomainVersionControl
            versions={domainVersions}
            selectedVersion={selectedVersion}
            onVersionChange={handleVersionChange}
          />
          <ProcessingControls
            isRunning={isProcessing}
            error={error}
            onStart={startPipeline}
            onStop={stopPipeline}
            isStartDisabled={!selectedVersion || domainFiles.length === 0}
          />
        </VStack>

        {/* Main Two-Panel Layout */}
        <Flex gap="6" h="calc(100vh - 200px)">
          {/* Chat Panel */}
          <Box flex={showRightPanel ? 1 : 2} minW="0">
            <ChatPanel
              parseVersions={pipeline?.parse_versions || []}
              extractVersions={pipeline?.extract_versions || []}
              graphVersionId={pipeline?.latest_graph_version_id}
              pipeline={pipeline}
              onVisualizationUpdate={handleVisualizationUpdate}
            />
          </Box>

          {/* Right Panel Toggle */}
          <Flex>
            <IconButton
              aria-label={showRightPanel ? "Hide panel" : "Show panel"}
              icon={showRightPanel ? <ChevronRight /> : <ChevronLeft />}
              onClick={() => setShowRightPanel(!showRightPanel)}
              position="relative"
              right={0}
              top="50%"
              transform="translateY(-50%)"
              zIndex={2}
              size="sm"
              variant="solid"
              colorScheme="gray"
              border="1px solid"
              borderColor="gray.200"
              borderRadius="md 0 0 md"
            />

            {/* Right Panel Content */}
            {showRightPanel && (
              <Box flex={1} minW="0">
                <ProcessingStatusPanel
                  isProcessing={isProcessing}
                  currentStage={pipeline?.stage || 'NOT_STARTED'}
                  results={processingResults}
                  visualization={visualization}
                />
              </Box>
            )}
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
};

export default ProcessingWorkspace;