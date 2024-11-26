import React, { useState, useEffect, useContext } from 'react';
import {
    VStack,
    Text,
    List,
    ListItem,
    Flex,
    Icon,
    Box,
    Badge,
    Progress,
    Button,
    HStack,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
    useToast,
    SimpleGrid,
    Accordion,
    AccordionItem,
    AccordionButton,
    AccordionPanel,
    AccordionIcon,
} from '@chakra-ui/react';
import {
    CheckCircleIcon,
    WarningIcon,
    DownloadIcon,
    RepeatIcon,
    ViewIcon,
} from '@chakra-ui/icons';
import BaseStage from './BaseStage';
import AuthContext from '../../../context/AuthContext';

const OntologyStage = ({
    domainId,
    version,
    pipelineId,
    onComplete,
    onPipelineCreate,
    processing,
    setProcessing,
}) => {
    const [status, setStatus] = useState('pending');
    const [ontologyStats, setOntologyStats] = useState(null);
    const [groups, setGroups] = useState([]);
    const [activeTab, setActiveTab] = useState(0);
    const [validationResults, setValidationResults] = useState(null);
    const toast = useToast();
    const { token, currentTenant } = useContext(AuthContext);

    useEffect(() => {
        fetchGroups();
        if (status === 'completed') {
            fetchOntologyStats();
        }
    }, [domainId, status]);

    const fetchGroups = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/process/tenants/${currentTenant}/domains/${domainId}/groups`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch groups');
            const data = await response.json();
            setGroups(data);
        } catch (error) {
            console.error('Error fetching groups:', error);
            toast({
                title: 'Error fetching groups',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const fetchOntologyStats = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/process/tenants/${currentTenant}/domains/${domainId}/ontology/stats`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );
            if (!response.ok) throw new Error('Failed to fetch ontology statistics');
            const data = await response.json();
            setOntologyStats(data);
        } catch (error) {
            console.error('Error fetching ontology stats:', error);
            toast({
                title: 'Error fetching ontology statistics',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleStart = async () => {
        setProcessing(true);
        setStatus('processing');

        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/process/tenants/${currentTenant}/domains/${domainId}/ontology`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ pipelineId }),
                }
            );

            if (!response.ok) throw new Error('Failed to generate ontology');

            const data = await response.json();
            setOntologyStats(data.stats);
            setStatus('completed');
            onComplete();

            toast({
                title: 'Ontology generated successfully',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error during ontology generation:', error);
            setStatus('failed');
            toast({
                title: 'Error generating ontology',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setProcessing(false);
        }
    };

    const handleValidate = async () => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/process/tenants/${currentTenant}/domains/${domainId}/ontology/validate`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error('Failed to validate ontology');

            const results = await response.json();
            setValidationResults(results);

            toast({
                title: 'Validation completed',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error validating ontology:', error);
            toast({
                title: 'Error validating ontology',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleDownload = async (format) => {
        try {
            const response = await fetch(
                `${process.env.REACT_APP_BACKEND_URL}/process/tenants/${currentTenant}/domains/${domainId}/ontology/export?format=${format}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) throw new Error(`Failed to download ${format} format`);

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ontology.${format.toLowerCase()}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            toast({
                title: 'Download started',
                description: `Downloading ontology in ${format} format`,
                status: 'success',
                duration: 3000,
                isClosable: true,
            });
        } catch (error) {
            console.error('Error downloading ontology:', error);
            toast({
                title: 'Download failed',
                description: error.message,
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    return (
        <BaseStage
            title="Create Ontology"
            description="Generate a formal ontology structure from grouped concepts"
            status={status}
            onStart={handleStart}
            onRetry={handleStart}
            processing={processing}
        >
            <Tabs
                variant="enclosed"
                onChange={setActiveTab}
                index={activeTab}
                mt={4}
            >
                <TabList>
                    <Tab>Input Groups</Tab>
                    <Tab>Statistics</Tab>
                    <Tab>Validation</Tab>
                    <Tab>Export</Tab>
                </TabList>

                <TabPanels>
                    <TabPanel>
                        <VStack spacing={4} align="stretch">
                            <Text fontWeight="bold">Available Groups for Ontology Generation:</Text>
                            <Accordion allowMultiple>
                                {groups.map((group, index) => (
                                    <AccordionItem key={index}>
                                        <h2>
                                            <AccordionButton>
                                                <Box flex="1" textAlign="left">
                                                    <Text fontWeight="semibold">{group.name}</Text>
                                                </Box>
                                                <Badge colorScheme="blue" mr={2}>
                                                    {group.entityCount} entities
                                                </Badge>
                                                <AccordionIcon />
                                            </AccordionButton>
                                        </h2>
                                        <AccordionPanel>
                                            <VStack align="stretch" spacing={2}>
                                                <Text fontSize="sm">Description: {group.description}</Text>
                                                <Text fontSize="sm">Created: {new Date(group.createdAt).toLocaleString()}</Text>
                                                <Badge colorScheme={group.validated ? "green" : "yellow"}>
                                                    {group.validated ? "Validated" : "Pending Validation"}
                                                </Badge>
                                            </VStack>
                                        </AccordionPanel>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        </VStack>
                    </TabPanel>

                    <TabPanel>
                        {ontologyStats ? (
                            <Box p={4} borderRadius="md" bg="gray.50">
                                <Text fontWeight="bold" mb={3}>Ontology Statistics:</Text>
                                <SimpleGrid columns={2} spacing={4}>
                                    <StatBox
                                        label="Classes"
                                        value={ontologyStats.classes}
                                        colorScheme="blue"
                                    />
                                    <StatBox
                                        label="Properties"
                                        value={ontologyStats.properties}
                                        colorScheme="green"
                                    />
                                    <StatBox
                                        label="Relationships"
                                        value={ontologyStats.relationships}
                                        colorScheme="purple"
                                    />
                                    <StatBox
                                        label="Axioms"
                                        value={ontologyStats.axioms}
                                        colorScheme="orange"
                                    />
                                </SimpleGrid>

                                <Box mt={4}>
                                    <Text mb={1}>Consistency Score:</Text>
                                    <Progress
                                        value={ontologyStats.consistency * 100}
                                        colorScheme="green"
                                        hasStripe
                                    />
                                    <Text fontSize="sm" textAlign="right" mt={1}>
                                        {(ontologyStats.consistency * 100).toFixed(1)}%
                                    </Text>
                                </Box>
                            </Box>
                        ) : (
                            <Text>No statistics available. Generate the ontology first.</Text>
                        )}
                    </TabPanel>

                    <TabPanel>
                        <VStack spacing={4} align="stretch">
                            <HStack>
                                <Button
                                    leftIcon={<RepeatIcon />}
                                    colorScheme="blue"
                                    onClick={handleValidate}
                                    isDisabled={!ontologyStats || status !== 'completed'}
                                >
                                    Run Validation
                                </Button>
                                <Button
                                    leftIcon={<ViewIcon />}
                                    variant="outline"
                                    onClick={() => {/* Implement detailed view */ }}
                                    isDisabled={!validationResults}
                                >
                                    View Details
                                </Button>
                            </HStack>

                            {validationResults && (
                                <Box mt={4} p={4} borderRadius="md" bg="gray.50">
                                    <Text fontWeight="bold" mb={3}>Validation Results:</Text>
                                    <List spacing={3}>
                                        {validationResults.checks.map((check, index) => (
                                            <ListItem key={index}>
                                                <Flex justify="space-between" align="center">
                                                    <Text>{check.name}</Text>
                                                    <Badge
                                                        colorScheme={check.passed ? "green" : "red"}
                                                    >
                                                        {check.passed ? "Passed" : "Failed"}
                                                    </Badge>
                                                </Flex>
                                                {!check.passed && (
                                                    <Text fontSize="sm" color="red.500" mt={1}>
                                                        {check.message}
                                                    </Text>
                                                )}
                                            </ListItem>
                                        ))}
                                    </List>
                                </Box>
                            )}
                        </VStack>
                    </TabPanel>

                    <TabPanel>
                        <VStack spacing={4} align="stretch">
                            <Text fontWeight="bold">Export Ontology:</Text>
                            <SimpleGrid columns={2} spacing={4}>
                                <ExportButton
                                    format="OWL"
                                    description="Web Ontology Language format"
                                    onClick={() => handleDownload('OWL')}
                                    isDisabled={!ontologyStats || status !== 'completed'}
                                />
                                <ExportButton
                                    format="RDF"
                                    description="Resource Description Framework"
                                    onClick={() => handleDownload('RDF')}
                                    isDisabled={!ontologyStats || status !== 'completed'}
                                />
                                <ExportButton
                                    format="JSON-LD"
                                    description="JSON for Linked Data"
                                    onClick={() => handleDownload('JSON-LD')}
                                    isDisabled={!ontologyStats || status !== 'completed'}
                                />
                                <ExportButton
                                    format="TTL"
                                    description="Turtle format"
                                    onClick={() => handleDownload('TTL')}
                                    isDisabled={!ontologyStats || status !== 'completed'}
                                />
                            </SimpleGrid>
                        </VStack>
                    </TabPanel>
                </TabPanels>
            </Tabs>
        </BaseStage>
    );
};

// Helper Components
const StatBox = ({ label, value, colorScheme }) => (
    <Box p={4} borderRadius="md" bg="white" shadow="sm" border="1px" borderColor="gray.200">
        <Text fontSize="sm" color="gray.600">{label}</Text>
        <Flex justify="space-between" align="center" mt={1}>
            <Text fontSize="2xl" fontWeight="bold">{value}</Text>
            <Badge colorScheme={colorScheme} fontSize="sm">
                {value > 0 ? "Present" : "None"}
            </Badge>
        </Flex>
    </Box>
);

const ExportButton = ({ format, description, onClick, isDisabled }) => (
    <Button
        leftIcon={<DownloadIcon />}
        onClick={onClick}
        isDisabled={isDisabled}
        variant="outline"
        colorScheme="blue"
        size="lg"
        width="full"
        height="auto"
        py={4}
    >
        <VStack spacing={1} align="start">
            <Text>{format}</Text>
            <Text fontSize="xs" color="gray.600">
                {description}
            </Text>
        </VStack>
    </Button>
);

export default OntologyStage;