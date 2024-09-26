import React, { useEffect, useState, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ReactFlow, addEdge, useNodesState, useEdgesState } from '@xyflow/react';
import dagre from 'dagre';  // Import dagre for auto layout
import '@xyflow/react/dist/style.css';
import { Box, Heading, Container, Text, Flex, Badge, Button, Link } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext'; // Correct path for AuthContext

const nodeWidth = 200;
const nodeHeight = 100;

// Define the layout function with improved settings
const getLayoutedNodes = (nodes, edges) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // Configure the layout: Top-to-Bottom (TB), with increased separation between ranks and nodes
  dagreGraph.setGraph({
    rankdir: 'TB',  // Top-to-Bottom layout
    ranksep: 150,   // Increase vertical spacing between ranks
    nodesep: 100,   // Increase horizontal spacing between nodes
  });

  // Add nodes to dagre graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  // Add edges to dagre graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Perform layout calculation
  dagre.layout(dagreGraph);

  // Update node positions based on layout
  return nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
    return node;
  });
};

const DomainPage = () => {
  const { domain_id } = useParams();  // Get the domain ID from the URL
  const [concepts, setConcepts] = useState([]);
  const [methodologies, setMethodologies] = useState([]);  // State for methodologies
  const [sources, setSources] = useState([]);  // State for sources
  const [selectedNode, setSelectedNode] = useState(null);  // State for selected node
  const { token } = useContext(AuthContext);  // Get the token from AuthContext
  const navigate = useNavigate();

  // Use useNodesState and useEdgesState from @xyflow/react for controlled flow
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Function to generate flow elements (nodes and edges)
  const generateFlowElements = (concepts, methodologies, sources, relationships) => {
    const typeColors = {
      definition: '#FFB6C1',   // Light Pink
      process: '#ADD8E6',      // Light Blue
      methodology: '#90EE90',  // Light Green
      source: '#FFD700',       // Gold
      other: '#FFA07A',        // Light Salmon
    };

    // Generate concept nodes
    const conceptNodes = concepts.map((concept) => ({
      id: concept.concept_id,
      data: { label: concept.name, type: 'concept', description: concept.description },
      style: {
        background: typeColors[concept.type] || typeColors.other,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
      width: nodeWidth,
      height: nodeHeight,
    }));

    // Generate methodology nodes
    const methodologyNodes = methodologies.map((methodology) => ({
      id: methodology.methodology_id,
      data: { label: methodology.name, type: 'methodology', description: methodology.description },
      style: {
        background: typeColors.methodology,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
      width: nodeWidth,
      height: nodeHeight,
    }));

    // Generate source nodes
    const sourceNodes = sources.map((source) => ({
      id: source.source_id,
      data: { label: source.name, type: 'source', description: source.description },
      style: {
        background: typeColors.source,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
      width: nodeWidth,
      height: nodeHeight,
    }));

    // Combine all nodes into one array
    const allNodes = [...conceptNodes, ...methodologyNodes, ...sourceNodes];

    // Generate edges from relationships, mapping entity_id_1 and entity_id_2 to source and target
    const relationshipEdges = relationships
      .map((rel) => {
        const source = rel.entity_id_1;
        const target = rel.entity_id_2;

        if (allNodes.some(node => node.id === source) && allNodes.some(node => node.id === target)) {
          return {
            id: `e${source}-${target}`,
            source,
            target,
            animated: true,
            style: { stroke: '#4682B4', strokeWidth: 2 },
          };
        }
        return null;
      })
      .filter(edge => edge !== null);

    // Use Dagre to optimize the layout
    const layoutedNodes = getLayoutedNodes(allNodes, relationshipEdges);

    // Log the final nodes and edges for further debugging
    console.log('Generated Nodes:', layoutedNodes);
    console.log('Generated Edges:', relationshipEdges);

    // Set nodes and edges in state
    setNodes(layoutedNodes);
    setEdges(relationshipEdges);
  };

  // Fetch relationships between all elements (concepts, methodologies, sources)
  const fetchRelationships = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/relationships`, {
        headers: {
          Authorization: `Bearer ${token}`,  // Include token in the request headers
        },
      });
      const data = await response.json();
      if (response.ok) {
        console.log('Fetched Relationships:', data); // Log relationships data
        return data;  // Return relationships data
      } else {
        console.error(`Failed to fetch relationships for domain ${domain_id}`);
        return [];
      }
    } catch (error) {
      console.error(`Error fetching relationships for domain ${domain_id}:`, error);
      return [];
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      if (!token) {
        console.error('No token found. User is not authenticated.');
        return;
      }

      try {
        // Fetch concepts
        const conceptResponse = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/concepts`, {
          headers: {
            Authorization: `Bearer ${token}`,  // Include token in the request headers
          },
        });

        // Fetch methodologies
        const methodologyResponse = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/methodologies`, {
          headers: {
            Authorization: `Bearer ${token}`,  // Include token in the request headers
          },
        });

        // Fetch sources
        const sourceResponse = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/sources`, {
          headers: {
            Authorization: `Bearer ${token}`,  // Include token in the request headers
          },
        });

        const conceptsData = await conceptResponse.json();
        const methodologiesData = await methodologyResponse.json();
        const sourcesData = await sourceResponse.json();

        // Log fetched data
        console.log('Fetched Concepts:', conceptsData);
        console.log('Fetched Methodologies:', methodologiesData);
        console.log('Fetched Sources:', sourcesData);

        if (conceptResponse.ok && methodologyResponse.ok && sourceResponse.ok) {
          setConcepts(conceptsData);
          setMethodologies(methodologiesData);
          setSources(sourcesData);

          // Fetch relationships between all elements
          const relationships = await fetchRelationships();

          // Generate flow elements based on concepts, methodologies, sources, and relationships
          generateFlowElements(conceptsData, methodologiesData, sourcesData, relationships);
        } else {
          console.error('Failed to fetch concepts, methodologies, or sources');
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    if (domain_id) {
      fetchData();
    }
  }, [domain_id, token]);

  // Handle new connections (adding edges)
  const onConnect = (params) => setEdges((eds) => addEdge(params, eds));

  // Handle node click to display info on the right
  const onNodeClick = (_, node) => {
    setSelectedNode(node);
  };

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading fontSize="2xl" mb={6}>
          Concepts, Methodologies, and Sources for Domain
        </Heading>

        <Flex justify="space-between">
          {/* Flow View */}
          <Box width="70%">
            {concepts.length > 0 || methodologies.length > 0 || sources.length > 0 ? (
              <Box height="500px" bg="white" borderRadius="md" boxShadow="md">
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={onNodeClick}
                  fitView  // Ensures all nodes fit within the view
                />
              </Box>
            ) : (
              <Text>No data found for this domain.</Text>
            )}
          </Box>

          {/* Information Panel */}
          <Box width="25%" p={4} bg="white" borderRadius="md" boxShadow="md">
            {selectedNode ? (
              <>
                <Heading size="md">{selectedNode.data.label}</Heading>
                <Text mt={2}><b>Type:</b> {selectedNode.data.type}</Text>
                <Text mt={2}><b>Description:</b> {selectedNode.data.description || 'No description available'}</Text>
              </>
            ) : (
              <Text>Select a node to see details</Text>
            )}
          </Box>
        </Flex>

        <Flex justify="center" mt={6}>
          <Button 
            colorScheme="blue" 
            size="lg" 
            onClick={() => navigate(`/domains/${domain_id}/config`)}  // Navigate to domain config page
          >
            View Domain Config
          </Button>
        </Flex>

        {/* Color Legend */}
        <Box mt={6} p={4} bg="white" borderRadius="md" boxShadow="md">
          <Heading size="sm">Color Legend</Heading>
          <Flex mt={2}>
            <Badge bg="#FFB6C1" color="white" mr={2}>Concept</Badge>
            <Badge bg="#90EE90" color="white" mr={2}>Methodology</Badge>
            <Badge bg="#FFD700" color="white" mr={2}>Source</Badge>
          </Flex>
        </Box>
      </Container>
    </Box>
  );
};

export default DomainPage;