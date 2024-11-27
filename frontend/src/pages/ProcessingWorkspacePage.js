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
    HStack,
    Icon,
    Textarea,
    Flex,
    Badge,
    Grid,
    GridItem,
    useColorModeValue,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import ChatPanel from '../components/chat/ChatPanel';

// Import stage components
import ParseStage from '../components/processing/stages/ParseStage';
import ExtractStage from '../components/processing/stages/ExtractStage';
import MergeStage from '../components/processing/stages/MergeStage';
import GroupStage from '../components/processing/stages/GroupStage';
import OntologyStage from '../components/processing/stages/OntologyStage';
import GraphStage from '../components/processing/stages/GraphStage';

const stages = [
    {
        id: 'version',
        name: 'Version',
        icon: '📋',
        description: 'Manage document versions',
        Component: () => (
            <Box bg="white" p={6} rounded="xl" shadow="sm" borderWidth={1} borderColor="gray.100">
                <Flex justify="space-between" align="center" mb={6}>
                    <Text fontSize="lg" fontWeight="medium">Current Version</Text>
                    <Badge colorScheme="blue" rounded="full" px={3}>Draft</Badge>
                </Flex>
                <VStack spacing={3}>
                    <Box w="full" p={4} bg="gray.50" rounded="lg">
                        <Flex justify="space-between" align="center">
                            <Box>
                                <Text fontWeight="medium">Gas Distribution v1.0</Text>
                                <Text fontSize="sm" color="gray.500">Created: Nov 27, 2024</Text>
                            </Box>
                            <Button size="sm" variant="outline">View Changes</Button>
                        </Flex>
                    </Box>
                </VStack>
            </Box>
        )
    },
    {
        id: 'parse',
        name: 'Parse',
        icon: '📄',
        description: 'Convert documents into processable text',
        Component: ParseStage
    },
    {
        id: 'extract',
        name: 'Extract',
        icon: '🔍',
        description: 'Identify domain-specific entities',
        Component: ExtractStage
    },
    {
        id: 'merge',
        name: 'Merge',
        icon: '🔄',
        description: 'Combine and deduplicate entities',
        Component: MergeStage
    },
    {
        id: 'group',
        name: 'Group',
        icon: '📊',
        description: 'Organize entities into groups',
        Component: GroupStage
    },
    {
        id: 'ontology',
        name: 'Ontology',
        icon: '🌐',
        description: 'Generate domain ontology',
        Component: OntologyStage
    },
    {
        id: 'graph',
        name: 'Graph',
        icon: '📈',
        description: 'Generate final knowledge graph',
        Component: GraphStage
    }
];

const ProcessingWorkspacePage = () => {
    const { domain_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const navigate = useNavigate();
    const toast = useToast();

    const [selectedStage, setSelectedStage] = useState('version');
    const [pipelineId, setPipelineId] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [domainInfo, setDomainInfo] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    const borderColor = useColorModeValue('gray.200', 'gray.700');
    const headerBg = useColorModeValue('white', 'gray.800');
    const activeBorderColor = useColorModeValue('blue.500', 'blue.300');
    const activeTextColor = useColorModeValue('blue.600', 'blue.300');

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
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (domain_id && currentTenant && token) {
            fetchDomainInfo();
        }
    }, [domain_id, currentTenant, token]);

    if (error) {
        return (
            <Container maxW="container.xl" py={8}>
                <Alert status="error" rounded="lg">
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

    const CurrentStageComponent = stages.find(s => s.id === selectedStage)?.Component;

    return (
        <Box h="100vh" display="flex" flexDirection="column">
            {/* Header */}
            <Box bg={headerBg} borderBottomWidth={1} borderColor={borderColor}>
                <Container maxW="container.xl" px={6}>
                    <Flex h="16" gap={8}>
                        {stages.map(stage => (
                            <Button
                                key={stage.id}
                                variant="ghost"
                                height="full"
                                px={1}
                                onClick={() => setSelectedStage(stage.id)}
                                position="relative"
                                borderRadius={0}
                                color={selectedStage === stage.id ? activeTextColor : 'gray.600'}
                                _hover={{ color: 'gray.900' }}
                                _after={{
                                    content: '""',
                                    position: 'absolute',
                                    bottom: '-1px',
                                    left: 0,
                                    right: 0,
                                    height: '2px',
                                    bg: selectedStage === stage.id ? activeBorderColor : 'transparent'
                                }}
                            >
                                <HStack spacing={2}>
                                    <Text>{stage.icon}</Text>
                                    <Text>{stage.name}</Text>
                                </HStack>
                            </Button>
                        ))}
                    </Flex>
                </Container>
            </Box>

            {/* Main Content */}
            <Grid
                flex={1}
                templateColumns="1fr 1fr"
                overflow="hidden"
            >
                {/* Chat Panel */}
                <Box
                    borderRightWidth={1}
                    borderColor={borderColor}
                    bg="white"
                >
                    <ChatPanel
                        domainId={domain_id}
                        currentStage={stages.find(s => s.id === selectedStage)}
                    />
                </Box>

                {/* Content Area */}
                <Box p={6} overflowY="auto">
                    <Box maxW="3xl" mx="auto">
                        {CurrentStageComponent && (
                            <CurrentStageComponent
                                domainId={domain_id}
                                pipelineId={pipelineId}
                                onPipelineCreate={setPipelineId}
                                processing={processing}
                                setProcessing={setProcessing}
                                token={token}
                                currentTenant={currentTenant}
                            />
                        )}
                    </Box>
                </Box>
            </Grid>
        </Box>
    );
};

export default ProcessingWorkspacePage;