import React, { useEffect, useState, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ReactFlow, addEdge, useNodesState, useEdgesState } from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import { Box, Heading, Container, Text, Flex, Badge, Button } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const nodeWidth = 200;
const nodeHeight = 100;

const getLayoutedNodes = (nodes, edges) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', ranksep: 150, nodesep: 100 });

  nodes.forEach((node) => dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight }));
  edges.forEach((edge) => dagreGraph.setEdge(edge.source, edge.target));
  dagre.layout(dagreGraph);

  return nodes.map((node) => {
    const { x, y } = dagreGraph.node(node.id);
    node.position = { x: x - nodeWidth / 2, y: y - nodeHeight / 2 };
    return node;
  });
};

const DomainPage = () => {
  const { domain_id } = useParams();
  const [concepts, setConcepts] = useState([]);
  const [methodologies, setMethodologies] = useState([]);
  const [sources, setSources] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const { token } = useContext(AuthContext);
  const navigate = useNavigate();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const generateFlowElements = (concepts, methodologies, sources, relationships) => {
    const typeColors = {
      definition: '#FFB6C1', process: '#ADD8E6', methodology: '#90EE90', source: '#FFD700', other: '#FFA07A',
    };

    const createNode = (item, type) => ({
      id: item[`${type}_id`],
      data: { label: item.name, type, description: item.description },
      style: {
        background: typeColors[type] || typeColors.other,
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
      width: nodeWidth,
      height: nodeHeight,
    });

    const allNodes = [
      ...concepts.map((c) => createNode(c, 'concept')),
      ...methodologies.map((m) => createNode(m, 'methodology')),
      ...sources.map((s) => createNode(s, 'source')),
    ];

    const relationshipEdges = relationships
      .map(({ entity_id_1: source, entity_id_2: target }) =>
        allNodes.some((n) => n.id === source) && allNodes.some((n) => n.id === target)
          ? { id: `e${source}-${target}`, source, target, animated: true, style: { stroke: '#4682B4', strokeWidth: 2 } }
          : null
      )
      .filter(Boolean);

    setNodes(getLayoutedNodes(allNodes, relationshipEdges));
    setEdges(relationshipEdges);
  };

  const fetchRelationships = async () => {
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/relationships`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok ? await res.json() : [];
    } catch {
      return [];
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;

      try {
        const [conceptsRes, methodologiesRes, sourcesRes] = await Promise.all([
          fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/concepts`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/methodologies`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/sources`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        const [conceptsData, methodologiesData, sourcesData] = await Promise.all([conceptsRes.json(), methodologiesRes.json(), sourcesRes.json()]);

        if (conceptsRes.ok && methodologiesRes.ok && sourcesRes.ok) {
          setConcepts(conceptsData);
          setMethodologies(methodologiesData);
          setSources(sourcesData);

          const relationships = await fetchRelationships();
          generateFlowElements(conceptsData, methodologiesData, sourcesData, relationships);
        }
      } catch {}
    };

    if (domain_id) fetchData();
  }, [domain_id, token]);

  const onConnect = (params) => setEdges((eds) => addEdge(params, eds));
  const onNodeClick = (_, node) => setSelectedNode(node);

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading fontSize="2xl" mb={6}>Concepts, Methodologies, and Sources for Domain</Heading>
        <Flex justify="space-between">
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
                  fitView
                />
              </Box>
            ) : <Text>No data found for this domain.</Text>}
          </Box>
          <Box width="25%" p={4} bg="white" borderRadius="md" boxShadow="md">
            {selectedNode ? (
              <>
                <Heading size="md">{selectedNode.data.label}</Heading>
                <Text mt={2}><b>Type:</b> {selectedNode.data.type}</Text>
                <Text mt={2}><b>Description:</b> {selectedNode.data.description || 'No description available'}</Text>
              </>
            ) : <Text>Select a node to see details</Text>}
          </Box>
        </Flex>
        <Flex justify="center" mt={6}>
          <Button colorScheme="blue" size="lg" onClick={() => navigate(`/domains/${domain_id}/config`)}>
            View Domain Config
          </Button>
        </Flex>
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