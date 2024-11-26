import React, { useState, useEffect, useContext } from 'react';
import {
    Box,
    Container,
    Text,
    Alert,
    AlertIcon,
    Button,
    useToast,
    Progress,
    VStack,
    Grid,
    GridItem,
    HStack,
    Badge,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';

// Import stage components
import ParseStage from '../components/processing/stages/ParseStage';
import ExtractStage from '../components/processing/stages/ExtractStage';
import MergeStage from '../components/processing/stages/MergeStage';
import GroupStage from '../components/processing/stages/GroupStage';
import OntologyStage from '../components/processing/stages/OntologyStage';
import GraphStage from '../components/processing/stages/GraphStage';
import ChatPanel from '../components/chat/ChatPanel';


const stages = [
    {
        id: 'parse',
        title: 'Parse Documents',
        description: 'Convert documents into processable text',
        Component: ParseStage
    },
    {
        id: 'extract',
        title: 'Extract Entities',
        description: 'Identify domain-specific entities',
        Component: ExtractStage
    },
    {
        id: 'merge',
        title: 'Merge Entities',
        description: 'Combine and deduplicate entities',
        Component: MergeStage
    },
    {
        id: 'group',
        title: 'Group Concepts',
        description: 'Organize entities into groups',
        Component: GroupStage
    },
    {
        id: 'ontology',
        title: 'Create Ontology',
        description: 'Generate domain ontology',
        Component: OntologyStage
    },
    {
        id: 'graph',
        title: 'Knowledge Graph',
        description: 'Generate final knowledge graph',
        Component: GraphStage
    }
];

const ProcessingWorkspacePage = () => {
    const { domain_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const navigate = useNavigate();
    const toast = useToast();

    const [currentStage, setCurrentStage] = useState(0);
    const [pipelineId, setPipelineId] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [domainInfo, setDomainInfo] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

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

    useEffect(() => {
        if (domain_id && currentTenant && token) {
            fetchDomainInfo();
            setLoading(false);
        }
    }, [domain_id, currentTenant, token]);

    const handleStageComplete = async () => {
        if (currentStage < stages.length - 1) {
            setCurrentStage(currentStage + 1);
            toast({
                title: `${stages[currentStage].title} completed`,
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

    const CurrentStage = stages[currentStage].Component;

    return (
        <Box minH="100vh" bg="gray.50" p={8}>
            <Container maxW="container.xl">
                {/* Header */}
                <HStack justify="space-between" mb={8}>
                    <VStack align="start" spacing={1}>
                        <Text fontSize="2xl" fontWeight="bold">
                            {domainInfo?.domain_name || 'Domain Processing'}
                        </Text>
                        <Text color="gray.600">
                            {domainInfo?.description}
                        </Text>
                    </VStack>
                    <Button variant="outline" onClick={() => navigate('/dashboard')}>
                        Back to Dashboard
                    </Button>
                </HStack>

                {/* Main Content + Chat Layout */}
                <Grid templateColumns="1fr 400px" gap={8}>
                    {/* Main Content */}
                    <GridItem>
                        <VStack spacing={8} align="stretch">
                            {/* Stage Progress */}
                            <Box bg="white" p={6} rounded="lg" shadow="sm">
                                <Box mb={6}>
                                    <HStack spacing={8} mb={4}>
                                        {stages.map((stage, index) => (
                                            <VStack
                                                key={stage.id}
                                                spacing={2}
                                                cursor={index <= currentStage ? "pointer" : "not-allowed"}
                                                opacity={index <= currentStage ? 1 : 0.5}
                                                onClick={() => {
                                                    if (index <= currentStage) {
                                                        setCurrentStage(index);
                                                    }
                                                }}
                                            >
                                                <Box
                                                    w="10"
                                                    h="10"
                                                    rounded="full"
                                                    bg={index === currentStage ? "blue.500" : "gray.200"}
                                                    color={index === currentStage ? "white" : "gray.500"}
                                                    display="flex"
                                                    alignItems="center"
                                                    justifyContent="center"
                                                    fontWeight="bold"
                                                >
                                                    {index + 1}
                                                </Box>
                                                <Text
                                                    fontSize="sm"
                                                    fontWeight={index === currentStage ? "bold" : "normal"}
                                                    color={index === currentStage ? "blue.500" : "gray.500"}
                                                >
                                                    {stage.title}
                                                </Text>
                                            </VStack>
                                        ))}
                                    </HStack>
                                    <Progress
                                        value={((currentStage + 1) / stages.length) * 100}
                                        size="sm"
                                        colorScheme="blue"
                                        rounded="full"
                                    />
                                </Box>
                            </Box>

                            {/* Current Stage */}
                            <Box bg="white" p={6} rounded="lg" shadow="sm">
                                <CurrentStage
                                    domainId={domain_id}
                                    pipelineId={pipelineId}
                                    onComplete={handleStageComplete}
                                    onPipelineCreate={setPipelineId}
                                    processing={processing}
                                    setProcessing={setProcessing}
                                    token={token}
                                    currentTenant={currentTenant}
                                />
                            </Box>
                        </VStack>
                    </GridItem>

                    {/* Chat Panel */}
                    <GridItem>
                        <ChatPanel
                            domainId={domain_id}
                            currentStage={stages[currentStage]}
                        />
                    </GridItem>
                </Grid>
            </Container>
        </Box>
    );
};

export default ProcessingWorkspacePage;