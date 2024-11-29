import React, { useState, useEffect, useContext } from 'react';
import {
    Box,
    Container,
    Heading,
    VStack,
    HStack,
    Text,
    Button,
    Select,
    Flex,
    Spinner,
    Alert,
    AlertIcon,
    useToast,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
    Badge,
    IconButton,
    Drawer,
    DrawerBody,
    DrawerHeader,
    DrawerOverlay,
    DrawerContent,
    DrawerCloseButton,
    useDisclosure,
    SimpleGrid,
    Checkbox,
} from '@chakra-ui/react';
import { useParams } from 'react-router-dom';
import {
    SettingsIcon,
    DownloadIcon,
    SearchIcon,
    InfoIcon,
} from '@chakra-ui/icons';
import AuthContext from '../context/AuthContext';

// Dummy visualization component - replace with your actual graph visualization
const GraphVisualization = ({ data, settings }) => (
    <Box
        h="600px"
        border="1px"
        borderColor="gray.200"
        borderRadius="lg"
        p={4}
        bg="white"
    >
        {/* Replace this with your actual graph visualization component */}
        <Text>Graph Visualization Component</Text>
        <Text color="gray.500">Number of nodes: {data?.nodes?.length || 0}</Text>
        <Text color="gray.500">Number of edges: {data?.edges?.length || 0}</Text>
    </Box>
);

const KnowledgeGraphPage = () => {
    const { domain_id } = useParams();
    const { token, currentTenant } = useContext(AuthContext);
    const toast = useToast();
    const { isOpen, onOpen, onClose } = useDisclosure();

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [graphData, setGraphData] = useState(null);
    const [selectedVersion, setSelectedVersion] = useState(null);
    const [versions, setVersions] = useState([]);
    const [viewSettings, setViewSettings] = useState({
        showLabels: true,
        showRelationships: true,
        showAttributes: false,
        layoutType: 'force',
        filterType: 'all',
    });

    useEffect(() => {
        fetchVersions();
    }, [domain_id]);

    useEffect(() => {
        if (selectedVersion) {
            fetchGraphData();
        }
    }, [selectedVersion]);

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

            // Select the latest validated version by default
            const latestValidated = data.find(v => v.status === 'validated');
            if (latestValidated) {
                setSelectedVersion(latestValidated.version_id);
            }
        } catch (error) {
            console.error('Error fetching versions:', error);
            setError(error.message);
        }
    };

    const fetchGraphData = async () => {
        setLoading(true);
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions/${selectedVersion}/graph`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to fetch graph data');
            const data = await response.json();
            setGraphData(data);
        } catch (error) {
            console.error('Error fetching graph data:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/versions/${selectedVersion}/graph/export?format=${format}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error(`Failed to export graph as ${format}`);

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `knowledge-graph.${format.toLowerCase()}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            toast({
                title: 'Export successful',
                description: `Graph exported as ${format}`,
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error exporting graph:', error);
            toast({
                title: 'Export failed',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleSettingsChange = (setting, value) => {
        setViewSettings(prev => ({
            ...prev,
            [setting]: value
        }));
    };

    if (error) {
        return (
            <Container maxW="container.xl" py={8}>
                <Alert status="error">
                    <AlertIcon />
                    {error}
                </Alert>
            </Container>
        );
    }

    return (
        <Box minH="100vh" bg="gray.50" py={8}>
            <Container maxW="container.xl">
                <VStack spacing={8} align="stretch">
                    <Flex justify="space-between" align="center">
                        <VStack align="start" spacing={1}>
                            <Heading size="lg">Knowledge Graph</Heading>
                            <HStack>
                                <Text color="gray.600">Version:</Text>
                                <Select
                                    w="auto"
                                    value={selectedVersion || ''}
                                    onChange={(e) => setSelectedVersion(e.target.value)}
                                >
                                    <option value="">Select a version</option>
                                    {versions.map((version) => (
                                        <option key={version.version_id} value={version.version_id}>
                                            Version {version.version_number} ({version.status})
                                        </option>
                                    ))}
                                </Select>
                            </HStack>
                        </VStack>

                        <HStack spacing={4}>
                            <Button
                                leftIcon={<SearchIcon />}
                                variant="outline"
                                onClick={() => {/* Implement search */ }}
                            >
                                Search
                            </Button>
                            <Button
                                leftIcon={<DownloadIcon />}
                                onClick={() => handleExport('JSON')}
                                isDisabled={!graphData}
                            >
                                Export
                            </Button>
                            <IconButton
                                icon={<SettingsIcon />}
                                onClick={onOpen}
                                aria-label="Settings"
                            />
                        </HStack>
                    </Flex>

                    {loading ? (
                        <Flex justify="center" align="center" h="600px">
                            <Spinner size="xl" />
                        </Flex>
                    ) : (
                        <Tabs>
                            <TabList>
                                <Tab>Graph View</Tab>
                                <Tab>Statistics</Tab>
                                <Tab>Insights</Tab>
                            </TabList>

                            <TabPanels>
                                <TabPanel>
                                    <GraphVisualization
                                        data={graphData}
                                        settings={viewSettings}
                                    />
                                </TabPanel>

                                <TabPanel>
                                    <Box bg="white" p={6} borderRadius="lg" shadow="sm">
                                        <Heading size="md" mb={4}>Graph Statistics</Heading>
                                        <SimpleGrid columns={3} spacing={6}>
                                            <StatBox
                                                label="Total Nodes"
                                                value={graphData?.nodes?.length || 0}
                                                type="nodes"
                                            />
                                            <StatBox
                                                label="Total Edges"
                                                value={graphData?.edges?.length || 0}
                                                type="edges"
                                            />
                                            <StatBox
                                                label="Density"
                                                value={(graphData?.density || 0).toFixed(2)}
                                                type="density"
                                            />
                                        </SimpleGrid>
                                    </Box>
                                </TabPanel>

                                <TabPanel>
                                    <Box bg="white" p={6} borderRadius="lg" shadow="sm">
                                        <Heading size="md" mb={4}>Knowledge Insights</Heading>
                                        {/* Add your insights components here */}
                                    </Box>
                                </TabPanel>
                            </TabPanels>
                        </Tabs>
                    )}
                </VStack>
            </Container>

            <Drawer isOpen={isOpen} onClose={onClose} size="md">
                <DrawerOverlay />
                <DrawerContent>
                    <DrawerCloseButton />
                    <DrawerHeader>View Settings</DrawerHeader>

                    <DrawerBody>
                        <VStack spacing={6} align="stretch">
                            <Box>
                                <Text fontWeight="bold" mb={2}>Layout Type</Text>
                                <Select
                                    value={viewSettings.layoutType}
                                    onChange={(e) => handleSettingsChange('layoutType', e.target.value)}
                                >
                                    <option value="force">Force-Directed</option>
                                    <option value="hierarchical">Hierarchical</option>
                                    <option value="circular">Circular</option>
                                </Select>
                            </Box>

                            <Box>
                                <Text fontWeight="bold" mb={2}>Display Options</Text>
                                <VStack align="stretch">
                                    <Checkbox
                                        isChecked={viewSettings.showLabels}
                                        onChange={(e) => handleSettingsChange('showLabels', e.target.checked)}
                                    >
                                        Show Labels
                                    </Checkbox>
                                    <Checkbox
                                        isChecked={viewSettings.showRelationships}
                                        onChange={(e) => handleSettingsChange('showRelationships', e.target.checked)}
                                    >
                                        Show Relationships
                                    </Checkbox>
                                    <Checkbox
                                        isChecked={viewSettings.showAttributes}
                                        onChange={(e) => handleSettingsChange('showAttributes', e.target.checked)}
                                    >
                                        Show Attributes
                                    </Checkbox>
                                </VStack>
                            </Box>

                            <Box>
                                <Text fontWeight="bold" mb={2}>Filter Type</Text>
                                <Select
                                    value={viewSettings.filterType}
                                    onChange={(e) => handleSettingsChange('filterType', e.target.value)}
                                >
                                    <option value="all">All</option>
                                    <option value="concepts">Concepts Only</option>
                                    <option value="entities">Entities Only</option>
                                    <option value="relationships">Relationships Only</option>
                                </Select>
                            </Box>
                        </VStack>
                    </DrawerBody>
                </DrawerContent>
            </Drawer>
        </Box>
    );
};

// Helper Components
const StatBox = ({ label, value, type }) => (
    <Box p={4} borderRadius="md" bg="gray.50">
        <Text fontSize="sm" color="gray.600">{label}</Text>
        <Flex justify="space-between" align="center" mt={2}>
            <Text fontSize="2xl" fontWeight="bold">{value}</Text>
            <Badge
                colorScheme={
                    type === 'nodes' ? 'blue' :
                        type === 'edges' ? 'green' :
                            'purple'
                }
            >
                {type}
            </Badge>
        </Flex>
    </Box>
);

export default KnowledgeGraphPage;