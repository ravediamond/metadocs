import React, { useEffect, useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { ReactFlow, addEdge, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Box, Heading, Container, Text } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext'; // Correct path for AuthContext

const DomainPage = () => {
  const { domain_id } = useParams();  // Get the domain ID from the URL
  const [concepts, setConcepts] = useState([]);
  const [methodologies, setMethodologies] = useState([]);  // State for methodologies
  const [sources, setSources] = useState([]);  // State for sources
  const { token } = useContext(AuthContext);  // Get the token from AuthContext

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
    const conceptNodes = concepts.map((concept, index) => ({
      id: concept.concept_id,
      data: { label: concept.name },
      position: {
        x: (index % 4) * 200, // Grid layout
        y: Math.floor(index / 4) * 200,
      },
      style: {
        background: typeColors[concept.type] || typeColors.other,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
    }));

    // Generate methodology nodes
    const methodologyNodes = methodologies.map((methodology, index) => ({
      id: methodology.methodology_id,
      data: { label: methodology.name },
      position: {
        x: (index % 4) * 200 + 800, // Position them further right
        y: Math.floor(index / 4) * 200,
      },
      style: {
        background: typeColors.methodology,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
    }));

    // Generate source nodes
    const sourceNodes = sources.map((source, index) => ({
      id: source.source_id,
      data: { label: source.name },
      position: {
        x: (index % 4) * 200 + 1200, // Position them further right
        y: Math.floor(index / 4) * 200,
      },
      style: {
        background: typeColors.source,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
    }));

    // Combine all nodes into one array
    const allNodes = [...conceptNodes, ...methodologyNodes, ...sourceNodes];

    // Create a map of node IDs for easy lookup
    const nodeIds = new Set(allNodes.map(node => node.id));

    // Generate edges from relationships, mapping entity_id_1 and entity_id_2 to source and target
    const relationshipEdges = relationships
      .map((rel) => {
        // Determine the source and target based on entity_id_1 and entity_id_2
        const source = rel.entity_id_1;
        const target = rel.entity_id_2;

        // Log the source and target values for debugging
        console.log(`Processing relationship: source = ${source}, target = ${target}, entity_type_1 = ${rel.entity_type_1}, entity_type_2 = ${rel.entity_type_2}`);

        // Warn if the source or target doesn't exist
        if (!nodeIds.has(source)) {
          console.warn(`Warning: source ID ${source} not found in nodes`);
        }
        if (!nodeIds.has(target)) {
          console.warn(`Warning: target ID ${target} not found in nodes`);
        }

        // Only return edge if both source and target exist
        if (nodeIds.has(source) && nodeIds.has(target)) {
          return {
            id: `e${source}-${target}`,
            source: source,
            target: target,
            animated: true,
            style: { stroke: '#4682B4', strokeWidth: 2 },
          };
        }
        return null;  // If invalid, return null to filter it out later
      })
      .filter(edge => edge !== null);  // Filter out any null edges

    // Log the final nodes and edges for further debugging
    console.log('Generated Nodes:', allNodes);
    console.log('Generated Edges:', relationshipEdges);

    // Set nodes and edges in state
    setNodes(allNodes);
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

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading fontSize="2xl" mb={6}>
          Concepts, Methodologies, and Sources for Domain
        </Heading>

        {concepts.length > 0 || methodologies.length > 0 || sources.length > 0 ? (
          <Box height="500px" bg="white" borderRadius="md" boxShadow="md">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              fitView  // Ensures all nodes fit within the view
            />
          </Box>
        ) : (
          <Text>No data found for this domain.</Text>
        )}
      </Container>
    </Box>
  );
};

export default DomainPage;