import React, { useEffect, useState, useContext } from 'react';
import {
  Box, Heading, Container, Text, Flex, Badge, Button, Select, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalFooter, ModalBody, ModalCloseButton, useDisclosure
} from '@chakra-ui/react';
import { ReactFlow, addEdge, useNodesState, useEdgesState } from '@xyflow/react';
import { useParams, useNavigate } from 'react-router-dom';
import dagre from 'dagre';
import AuthContext from '../context/AuthContext';
import '@xyflow/react/dist/style.css';

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
  const { isOpen, onOpen, onClose } = useDisclosure(); // For "Add Node" modal
  const { isOpen: isRelOpen, onOpen: onRelOpen, onClose: onRelClose } = useDisclosure(); // For "Add Relationship" modal

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [newNodeType, setNewNodeType] = useState('concept');
  const [selectedSourceNode, setSelectedSourceNode] = useState('');
  const [selectedTargetNode, setSelectedTargetNode] = useState('');
  const [relationshipType, setRelationshipType] = useState('');

  const generateFlowElements = (concepts, methodologies, sources, relationships) => {
    const typeColors = {
      concept: '#FFB6C1', methodology: '#90EE90', source: '#FFD700', other: '#FFA07A',
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

  // Function to add a new node
  const addNewNode = async () => {
    const newNodeId = `new_node_${nodes.length + 1}`;
    const newNode = {
      id: newNodeId,
      data: { label: `New ${newNodeType} ${nodes.length + 1}`, type: newNodeType, description: 'This is a new node' },
      position: { x: Math.random() * 300, y: Math.random() * 300 },
      style: {
        background: newNodeType === 'concept' ? '#FFB6C1' : newNodeType === 'methodology' ? '#90EE90' : '#FFD700',
        borderRadius: '8px',
        padding: '10px',
        border: '2px solid #000',
      },
      width: nodeWidth,
      height: nodeHeight,
    };

    // Add new node to graph state
    setNodes((nds) => [...nds, newNode]);

    // Send node to backend
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/nodes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ label: `New ${newNodeType}`, type: newNodeType }),
      });
      if (!response.ok) throw new Error('Failed to register the new node.');
    } catch (error) {
      console.error('Error:', error);
    }

    onClose(); // Close the modal after adding a node
  };

  // Function to add a relationship
  const addRelationship = async () => {
    if (!selectedSourceNode || !selectedTargetNode || !relationshipType) return;

    const newEdge = {
      id: `e${selectedSourceNode}-${selectedTargetNode}`,
      source: selectedSourceNode,
      target: selectedTargetNode,
      animated: true,
      style: { stroke: '#4682B4', strokeWidth: 2 },
    };
    setEdges((eds) => [...eds, newEdge]);

    // Send relationship to backend
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/relationships`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          source_id: selectedSourceNode,
          target_id: selectedTargetNode,
          relationship_type: relationshipType,
        }),
      });
      if (!response.ok) throw new Error('Failed to register the new relationship.');
    } catch (error) {
      console.error('Error:', error);
    }

    onRelClose(); // Close the relationship modal
  };

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
          <Button colorScheme="green" size="lg" ml={4} onClick={onOpen}>
            Add New Node
          </Button>
          <Button colorScheme="teal" size="lg" ml={4} onClick={onRelOpen}>
            Add Relationship
          </Button>
        </Flex>

        {/* Modal for adding new node */}
        <Modal isOpen={isOpen} onClose={onClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Create a New Node</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Select placeholder="Select node type" value={newNodeType} onChange={(e) => setNewNodeType(e.target.value)} mb={4}>
                <option value="concept">Concept</option>
                <option value="methodology">Methodology</option>
                <option value="source">Source</option>
              </Select>
            </ModalBody>

            <ModalFooter>
              <Button colorScheme="green" onClick={addNewNode}>Add Node</Button>
              <Button variant="ghost" onClick={onClose}>Cancel</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Modal for adding relationship */}
        <Modal isOpen={isRelOpen} onClose={onRelClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Create a New Relationship</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Select placeholder="Select source node" value={selectedSourceNode} onChange={(e) => setSelectedSourceNode(e.target.value)} mb={4}>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.data.label} ({node.data.type})
                  </option>
                ))}
              </Select>
              <Select placeholder="Select target node" value={selectedTargetNode} onChange={(e) => setSelectedTargetNode(e.target.value)} mb={4}>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.data.label} ({node.data.type})
                  </option>
                ))}
              </Select>
              <Select placeholder="Select relationship type" value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)} mb={4}>
                <option value="depends_on">Depends On</option>
                <option value="related_to">Related To</option>
                <option value="part_of">Part Of</option>
              </Select>
            </ModalBody>

            <ModalFooter>
              <Button colorScheme="teal" onClick={addRelationship}>Add Relationship</Button>
              <Button variant="ghost" onClick={onRelClose}>Cancel</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

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