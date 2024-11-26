import React, { useState, useEffect, useContext } from 'react';
import {
    Box,
    Grid,
    GridItem,
    Heading,
    VStack,
    useToast,
    Progress,
    Container,
    Text,
    Alert,
    AlertIcon,
    Button,
    HStack,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import StageNavigation from '../components/processing/StageNavigation';
import ChatPanel from '../components/chat/ChatPanel';
import VersionControl from '../components/processing/VersionControl';

// Import all stage components
import ParseStage from '../components/processing/stages/ParseStage';
import ExtractStage from '../components/processing/stages/ExtractStage';
import MergeStage from '../components/processing/stages/MergeStage';
import GroupStage from '../components/processing/stages/GroupStage';
import OntologyStage from '../components/processing/stages/OntologyStage';

// Define stages with imported components
const stages = [
    {
        id: 'parse',
        name: 'Parse Documents',
        Component: ParseStage,
        description: 'Convert documents into processable text'
    },
    {
        id: 'extract',
        name: 'Extract Entities',
        Component: ExtractStage,
        description: 'Identify domain-specific entities'
    },
    {
        id: 'merge',
        name: 'Merge Knowledge',
        Component: MergeStage,
        description: 'Combine entities across documents'
    },
    {
        id: 'group',
        name: 'Group Concepts',
        Component: GroupStage,
        description: 'Organize entities into groups'
    },
    {
        id: 'ontology',
        name: 'Create Ontology',
        Component: OntologyStage,
        description: 'Generate domain ontology'
    }
];

const ProcessingWorkspacePage = () => {
    const { domain_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const navigate = useNavigate();
    const toast = useToast();

    const [currentStage, setCurrentStage] = useState(0);
    const [currentVersion, setCurrentVersion] = useState(null);
    const [versions, setVersions] = useState([]);
    const [pipelineId, setPipelineId] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [domainInfo, setDomainInfo] = useState(null);
    const [domainData, setDomainData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const initializeWorkspace = async () => {
            setLoading(true);
            try {
                await Promise.all([
                    fetchDomainInfo(),
                    fetchVersions()
                ]);
                await fetchDomainData();
            } catch (error) {
                console.error('Error initializing workspace:', error);
                if (!domainInfo) {
                    setError(error.message);
                }
            } finally {
                setLoading(false);
            }
        };

        if (domain_id && currentTenant && token) {
            initializeWorkspace();
        }
    }, [domain_id, currentTenant, token]);

    const fetchDomainInfo = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch domain information');
            const data = await response.json();
            setDomainInfo(data);

            if (data.latest_pipeline) {
                setPipelineId(data.latest_pipeline.pipeline_id);
            }
        } catch (error) {
            console.error('Error fetching domain info:', error);
            throw error;
        }
    };

    const fetchDomainData = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/data`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) {
                if (response.status !== 404) {
                    throw new Error('Failed to fetch domain data');
                }
                return;
            }
            const data = await response.json();
            setDomainData(data);
        } catch (error) {
            console.error('Error fetching domain data:', error);
        }
    };

    const fetchVersions = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch versions');
            const data = await response.json();
            setVersions(data);
            if (data.length > 0) {
                setCurrentVersion(data[data.length - 1]);
            }
        } catch (error) {
            console.error('Error fetching versions:', error);
            throw error;
        }
    };

    const handleVersionCreate = async () => {
        if (!pipelineId) {
            toast({
                title: 'Cannot create version',
                description: 'No completed processing pipeline available',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
            return;
        }

        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                    body: JSON.stringify({ processing_id: pipelineId })
                }
            );
            if (!response.ok) throw new Error('Failed to create version');
            const data = await response.json();
            setCurrentVersion(data);
            setVersions([...versions, data]);
            toast({
                title: 'New version created',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error creating version:', error);
            toast({
                title: 'Failed to create version',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleStageComplete = async () => {
        await fetchDomainData();

        if (currentStage < stages.length - 1) {
            setCurrentStage(currentStage + 1);
            toast({
                title: `${stages[currentStage].name} completed`,
                description: 'Moving to next stage',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } else {
            toast({
                title: 'Processing completed',
                description: 'All stages have been completed successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        }
    };

    // Get the current stage component
    const CurrentStage = stages[currentStage].Component;

    if (error) {
        return (
            <Container maxW="container.xl" py={8}>
                <Alert status="error" borderRadius="lg">
                    <AlertIcon />
                    {error}
                </Alert>
                <Button mt={4} onClick={() => navigate('/dashboard')}>
                    Return to Dashboard
                </Button>
            </Container>
        );
    }

    if (loading) {
        return (
            <Container maxW="container.xl" py={8}>
                <VStack spacing={4}>
                    <Text>Loading workspace...</Text>
                    <Progress size="xs" isIndeterminate w="100%" />
                </VStack>
            </Container>
        );
    }

    return (
        <Box minH="100vh" bg="gray.50">
            <Container maxW="container.xl" py={8}>
                <Grid templateColumns="3fr 1fr" gap={8}>
                    <GridItem>
                        <VStack spacing={8} align="stretch">
                            <Box bg="white" p={6} borderRadius="lg" shadow="sm">
                                <HStack justify="space-between" mb={6}>
                                    <VStack align="start" spacing={1}>
                                        <Heading size="lg">
                                            {domainInfo?.domain_name || 'Domain Processing'}
                                        </Heading>
                                        <Text color="gray.600">
                                            {domainInfo?.description}
                                        </Text>
                                    </VStack>
                                    <Button
                                        variant="outline"
                                        onClick={() => navigate('/dashboard')}
                                    >
                                        Back to Dashboard
                                    </Button>
                                </HStack>

                                <VersionControl
                                    currentVersion={currentVersion}
                                    versions={versions}
                                    onCreateVersion={handleVersionCreate}
                                    onSelectVersion={setCurrentVersion}
                                />

                                <Progress
                                    value={(currentStage / (stages.length - 1)) * 100}
                                    size="sm"
                                    colorScheme="blue"
                                    mb={6}
                                />

                                <StageNavigation
                                    stages={stages}
                                    currentStage={currentStage}
                                    onStageSelect={setCurrentStage}
                                />
                            </Box>

                            <Box bg="white" p={6} borderRadius="lg" shadow="sm">
                                <CurrentStage
                                    domainId={domain_id}
                                    version={currentVersion}
                                    pipelineId={pipelineId}
                                    onComplete={handleStageComplete}
                                    onPipelineCreate={setPipelineId}
                                    processing={processing}
                                    setProcessing={setProcessing}
                                    token={token}
                                    currentTenant={currentTenant}
                                    domainData={domainData}
                                />
                            </Box>
                        </VStack>
                    </GridItem>

                    <GridItem>
                        <ChatPanel
                            domainId={domain_id}
                            currentStage={stages[currentStage]}
                            token={token}
                            currentTenant={currentTenant}
                            domainData={domainData}
                        />
                    </GridItem>
                </Grid>
            </Container>
        </Box>
    );
};

export default ProcessingWorkspacePage;