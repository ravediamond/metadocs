import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactFlow, { MiniMap, Controls } from 'react-flow-renderer';
import { Box, Heading, Container, Text } from '@chakra-ui/react';

const DomainPage = () => {
  const { domain_id } = useParams(); // Get the domain ID from the URL
  const [concepts, setConcepts] = useState([]);
  const [elements, setElements] = useState([]); // For React Flow elements

  useEffect(() => {
    const fetchConcepts = async () => {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/concepts/${domain_id}`
      );
      const data = await response.json();
      if (response.ok) {
        setConcepts(data);
        generateFlowElements(data); // Generate flow elements based on the concepts
      } else {
        console.error('Failed to fetch concepts');
      }
    };

    if (domain_id) {
      fetchConcepts();
    }
  }, [domain_id]);

  // Function to generate React Flow elements (nodes and edges)
  const generateFlowElements = (concepts) => {
    const newElements = [];

    // Create nodes for each concept
    concepts.forEach((concept, index) => {
      newElements.push({
        id: concept.concept_id,
        data: { label: concept.name },
        position: { x: 100 * index, y: 100 }, // Position nodes dynamically
      });
    });

    // Create edges (relationships between nodes, if any)
    for (let i = 0; i < concepts.length - 1; i++) {
      newElements.push({
        id: `e${concepts[i].concept_id}-${concepts[i + 1].concept_id}`,
        source: concepts[i].concept_id,
        target: concepts[i + 1].concept_id,
        animated: true,
      });
    }

    setElements(newElements);
  };

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading fontSize="2xl" mb={6}>
          Concepts for Domain
        </Heading>

        {concepts.length > 0 ? (
          <Box height="500px" bg="white" borderRadius="md" boxShadow="md">
            <ReactFlow elements={elements}>
              <MiniMap />
              <Controls />
            </ReactFlow>
          </Box>
        ) : (
          <Text>No concepts found for this domain.</Text>
        )}
      </Container>
    </Box>
  );
};

export default DomainPage;