import React, { useState, useContext, useEffect } from 'react';
import { Box, Container, Flex, Text, IconButton, useToast } from '@chakra-ui/react';
import { Share2 } from 'lucide-react';
import AuthContext from '../context/AuthContext';
import ChatPanel from '../components/chat/ChatPanel';
import StageNavigation from '../components/processing/StageNavigation';
import VersionControl from '../components/processing/VersionControl';
import { stages } from '../constants/stages';

const StreamlinedWorkflow = () => {
  const { token, currentTenant } = useContext(AuthContext);
  const [currentStage, setCurrentStage] = useState('new-version');
  const [loading, setLoading] = useState(false);
  const [stageData, setStageData] = useState(null);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [versions, setVersions] = useState([]);
  const toast = useToast();

  const loadStageData = async () => {
    if (!token || !currentTenant) {
      toast({
        title: 'Authentication Error',
        description: 'Please log in to continue',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/process/tenants/${currentTenant}/stages/${currentStage}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) throw new Error('Failed to fetch stage data');
      const data = await response.json();
      setStageData(data);
    } catch (error) {
      console.error('Error loading stage data:', error);
      toast({
        title: 'Error loading data',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  };

  const loadVersions = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/versions/tenants/${currentTenant}/versions`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      if (!response.ok) throw new Error('Failed to fetch versions');
      const data = await response.json();
      setVersions(data);
    } catch (error) {
      console.error('Error fetching versions:', error);
      toast({
        title: 'Error fetching versions',
        description: error.message,
        status: 'error',
        duration: 3000,
      });
    }
  };

  useEffect(() => {
    if (token && currentTenant) {
      loadVersions();
      loadStageData();
    }
  }, [currentStage, token, currentTenant]);

  const handleCreateVersion = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/versions/tenants/${currentTenant}/versions`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: `Version ${versions.length + 1}`,
            status: 'draft'
          }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to create version');
      await loadVersions();
      return response.json();
    } catch (error) {
      throw error;
    }
  };

  const handleValidateVersion = async (versionId) => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/versions/tenants/${currentTenant}/versions/${versionId}/validate`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) throw new Error('Failed to validate version');
      await loadVersions();
      return response.json();
    } catch (error) {
      throw error;
    }
  };

  const handleStageChange = (stage) => {
    if (!currentVersion && stage !== 'new-version') {
      toast({
        title: 'Version required',
        description: 'Please create a version first',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    setCurrentStage(stage);
  };

  return (
    <Box h="100vh" display="flex" flexDirection="column" bg="gray.50">
      {/* Header */}
      <Box bg="white" borderBottom="1px" borderColor="gray.200">
        <Container maxW="container.xl" py={3}>
          <Flex justify="space-between" align="center" mb={4}>
            <Flex align="center" gap={4}>
              <Text fontSize="xl" fontWeight="semibold">
                Knowledge Graph Builder
              </Text>
              <StageNavigation 
                currentStage={currentStage}
                onStageChange={handleStageChange}
                activeVersion={currentVersion}
              />
            </Flex>
            <IconButton
              icon={<Share2 size={20} />}
              variant="ghost"
              aria-label="Share"
            />
          </Flex>
        </Container>
      </Box>

      {/* Main Content */}
      <Flex flex={1}>
        {/* Content Area */}
        <Box flex={1} p={6} overflowY="auto">
          <Box maxW="3xl" mx="auto">
            <VersionControl
              currentVersion={currentVersion}
              versions={versions}
              onCreateVersion={handleCreateVersion}
              onSelectVersion={setCurrentVersion}
              onValidateVersion={handleValidateVersion}
            />
            {loading ? (
              <Text>Loading...</Text>
            ) : (
              stageData && (
                <Box mt={4}>
                  {/* Render stage-specific content here */}
                  <pre>{JSON.stringify(stageData, null, 2)}</pre>
                </Box>
              )
            )}
          </Box>
        </Box>

        {/* Chat Panel */}
        <Box w="400px" borderLeft="1px" borderColor="gray.200">
          <ChatPanel 
            domainId={currentTenant}
            currentStage={{ id: currentStage, name: stages.find(s => s.id === currentStage)?.name }}
          />
        </Box>
      </Flex>
    </Box>
  );
};

export default StreamlinedWorkflow;