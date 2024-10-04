// DomainPage.jsx

import React, { useEffect, useState, useContext } from 'react';
import {
  Box, Heading, Container, Text, Flex, Button, Select, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalFooter, ModalBody, ModalCloseButton, Input, useDisclosure
} from '@chakra-ui/react';
import { ReactFlow, addEdge, useNodesState, useEdgesState, Controls, MiniMap } from '@xyflow/react';
import { useParams, useNavigate } from 'react-router-dom';
import dagre from 'dagre';
import AuthContext from '../context/AuthContext';
import '@xyflow/react/dist/style.css';
import { v4 as uuidv4 } from 'uuid'; // Import uuid

const nodeWidth = 200;
const nodeHeight = 100;

const getLayoutedNodes = (nodes, edges, existingPositions = {}) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', ranksep: 150, nodesep: 100 });

  nodes.forEach((node) => {
    const width = node.width || nodeWidth;
    const height = node.height || nodeHeight;
    dagreGraph.setNode(node.id, { width, height });
  });
  edges.forEach((edge) => dagreGraph.setEdge(edge.source, edge.target));
  dagre.layout(dagreGraph);

  return nodes.map((node) => {
    // Preserve existing positions
    if (existingPositions[node.id]) {
      node.position = existingPositions[node.id];
    } else {
      const { x, y } = dagreGraph.node(node.id);
      node.position = { x: x - nodeWidth / 2, y: y - nodeHeight / 2 };
    }
    return node;
  });
};

const DomainPage = () => {
  const { domain_id } = useParams();
  const [concepts, setConcepts] = useState([]);
  const [methodologies, setMethodologies] = useState([]);
  const [sources, setSources] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const { token, currentTenant } = useContext(AuthContext);
  const navigate = useNavigate();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isRelOpen, onOpen: onRelOpen, onClose: onRelClose } = useDisclosure();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesState] = useEdgesState([]);
  const [newNodeType, setNewNodeType] = useState('concept');
  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeDescription, setNewNodeDescription] = useState('');
  const [selectedSourceNode, setSelectedSourceNode] = useState('');
  const [selectedTargetNode, setSelectedTargetNode] = useState('');
  const [relationshipType, setRelationshipType] = useState('');
  const [currentVersion, setCurrentVersion] = useState(1);
  const [isModified, setIsModified] = useState(false);

  // New state variables for modals
  const [isNodeModalOpen, setIsNodeModalOpen] = useState(false);
  const [isEdgeModalOpen, setIsEdgeModalOpen] = useState(false);

  const generateFlowElements = (concepts, methodologies, sources, relationships) => {
    const typeColors = {
      concept: '#FFB6C1', methodology: '#90EE90', source: '#FFD700', other: '#FFA07A',
    };

    const createNode = (item, type) => {
      const nodeId = item[`${type}_id`];

      return {
        id: nodeId,
        data: {
          label: item.name,
          type,
          description: item.description,
          subtype: item.type || item.source_type || 'general',
          created_at: item.created_at,
          updated_at: item.updated_at,
          domain_version: item.domain_version, // Include domain_version
        },
        style: {
          background: typeColors[type] || typeColors.other,
          borderRadius: '12px',
          padding: '15px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        },
        width: nodeWidth,
        height: nodeHeight,
        position: { x: 0, y: 0 }, // Positions will be calculated
      };
    };

    // Create all nodes for concepts, methodologies, and sources
    const allNodes = [
      ...concepts.map((c) => createNode(c, 'concept')),
      ...methodologies.map((m) => createNode(m, 'methodology')),
      ...sources.map((s) => createNode(s, 'source')),
    ];

    // Create edges for relationships
    const relationshipEdges = relationships
      .map(({ relationship_id, entity_id_1: source, entity_id_2: target, relationship_type, created_at, updated_at, domain_version }) =>
        allNodes.some((n) => n.id === source) && allNodes.some((n) => n.id === target)
          ? {
              id: relationship_id,
              source,
              target,
              animated: true,
              style: { stroke: '#4682B4', strokeWidth: 2 },
              data: { relationship_type, created_at, updated_at, domain_version }, // Include domain_version
              label: relationship_type, // Add label to edge
              labelStyle: { fill: '#4682B4', fontWeight: 700 },
            }
          : null
      )
      .filter(Boolean);

    // Layout the nodes using dagre
    const layoutedNodes = getLayoutedNodes(allNodes, relationshipEdges);
    setNodes(layoutedNodes);
    setEdges(relationshipEdges);
  };

  const fetchData = async () => {
    if (!token) return;

    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/details`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const domainData = await res.json();
        console.log('Domain Data:', domainData);
        const { concepts, methodologies, sources, relationships, version } = domainData;
        setConcepts(concepts);
        setMethodologies(methodologies);
        setSources(sources);
        setCurrentVersion(version);

        generateFlowElements(concepts, methodologies, sources, relationships);
      }
    } catch {}
  };

  useEffect(() => {
    if (!currentTenant) {
      navigate('/select-tenant');
      return;
    }
    if (domain_id) fetchData();
  }, [domain_id, token, currentTenant, navigate]);

  const onConnect = (params) => {
    const newEdge = addEdge(params, edges);
    setEdges(newEdge);
    setIsModified(true);
  };

  const onNodeClick = (_, node) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    setIsNodeModalOpen(true);
  };

  const onEdgeClick = (_, edge) => {
    const sourceLabel = nodes.find(node => node.id === edge.source)?.data.label;
    const targetLabel = nodes.find(node => node.id === edge.target)?.data.label;

    setSelectedEdge({
      ...edge,
      sourceLabel,
      targetLabel,
    });
    setSelectedNode(null);
    setIsEdgeModalOpen(true);
  };

  const getNodeTypeById = (id) => {
    const node = nodes.find(node => node.id === id);
    return node ? node.data.type : null;
  };

  // Function to add a new node
  const addNewNode = () => {
    if (!newNodeName || !newNodeDescription) {
      alert('Please provide a name and description for the node');
      return;
    }

    const newNodeId = uuidv4(); // Generate a valid UUID

    const now = new Date().toISOString();

    const newNode = {
      id: newNodeId,
      data: {
        label: newNodeName,
        type: newNodeType,
        description: newNodeDescription,
        subtype: 'general', // Default subtype
        created_at: now,
        updated_at: now,
        domain_version: currentVersion, // Include domain_version
      },
      position: { x: 0, y: 0 }, // Position will be set by layout
      style: {
        background: newNodeType === 'concept' ? '#FFB6C1' : newNodeType === 'methodology' ? '#90EE90' : '#FFD700',
        borderRadius: '12px',
        padding: '15px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
      },
      width: nodeWidth,
      height: nodeHeight,
    };

    // Add the new node
    const updatedNodes = [...nodes, newNode];

    // Apply layout only to the new node
    const existingPositions = {};
    nodes.forEach(node => {
      existingPositions[node.id] = node.position;
    });

    const layoutedNodes = getLayoutedNodes(updatedNodes, edges, existingPositions);
    setNodes(layoutedNodes);
    setIsModified(true);

    onClose();
    setNewNodeName('');
    setNewNodeDescription('');
  };

  // Function to remove a node and its relationships
  const removeNode = async () => {
    if (!selectedNode) return;

    const nodeId = selectedNode.id;

    const updatedNodes = nodes.filter((node) => node.id !== nodeId);
    const updatedEdges = edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);

    setNodes(updatedNodes);
    setEdges(updatedEdges);
    setIsModified(true);

    const nodeType = selectedNode.data.type;
    const endpointMap = {
      concept: 'concepts',
      methodology: 'methodologies',
      source: 'sources',
    };

    const endpoint = endpointMap[nodeType];

    if (!endpoint) {
      console.error('Unknown node type:', nodeType);
      return;
    }

    try {
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/${endpoint}/${nodeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error('Error:', error);
    }

    setSelectedNode(null);
    setIsNodeModalOpen(false);
  };

  // Function to remove a relationship
  const removeRelationship = async () => {
    if (!selectedEdge) return;

    const edgeId = selectedEdge.id;

    const updatedEdges = edges.filter((edge) => edge.id !== edgeId);

    setEdges(updatedEdges);
    setIsModified(true);

    try {
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/relationships/${edgeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error('Error:', error);
    }

    setSelectedEdge(null);
    setIsEdgeModalOpen(false);
  };

  const addRelationship = () => {
    if (!selectedSourceNode || !selectedTargetNode || !relationshipType) return;

    const newEdgeId = uuidv4(); // Generate a valid UUID

    const now = new Date().toISOString();

    const newEdge = {
      id: newEdgeId,
      source: selectedSourceNode,
      target: selectedTargetNode,
      animated: true,
      style: { stroke: '#4682B4', strokeWidth: 2 },
      data: {
        relationship_type: relationshipType,
        created_at: now,
        updated_at: now,
        domain_version: currentVersion, // Include domain_version
      },
      label: relationshipType, // Add label to edge
      labelStyle: { fill: '#4682B4', fontWeight: 700 },
    };

    setEdges((eds) => [...eds, newEdge]);
    setIsModified(true);

    onRelClose();
  };

  const saveGraph = async () => {
    try {
      const now = new Date().toISOString();

      const concepts = nodes
        .filter(node => node.data.type === 'concept')
        .map(node => ({
          concept_id: node.id,
          name: node.data.label,
          description: node.data.description,
          type: node.data.subtype || 'general', // Provide a default type
          domain_id: domain_id,
          domain_version: node.data.domain_version || currentVersion,
          created_at: node.data.created_at || now,
          updated_at: now,
        }));

      const sources = nodes
        .filter(node => node.data.type === 'source')
        .map(node => ({
          source_id: node.id,
          name: node.data.label,
          description: node.data.description,
          source_type: node.data.subtype || 'general',
          location: node.data.location || '',
          domain_id: domain_id,
          domain_version: node.data.domain_version || currentVersion,
          created_at: node.data.created_at || now,
          updated_at: now,
        }));

      const methodologies = nodes
        .filter(node => node.data.type === 'methodology')
        .map(node => ({
          methodology_id: node.id,
          name: node.data.label,
          description: node.data.description,
          steps: node.data.steps || 'No steps provided',
          domain_id: domain_id,
          domain_version: node.data.domain_version || currentVersion,
          created_at: node.data.created_at || now,
          updated_at: now,
        }));

      const relationships = edges.map(edge => ({
        relationship_id: edge.id,
        entity_id_1: edge.source,
        entity_type_1: getNodeTypeById(edge.source),
        entity_id_2: edge.target,
        entity_type_2: getNodeTypeById(edge.target),
        relationship_type: edge.data.relationship_type,
        domain_id: domain_id,
        domain_version: edge.data.domain_version || currentVersion,
        created_at: edge.data.created_at || now,
        updated_at: now,
      }));

      const domainData = {
        concepts,
        sources,
        methodologies,
        relationships,
      };

      console.log('Data being sent to backend:', JSON.stringify(domainData, null, 2));

      // Send POST request to /domains/{domain_id}/save
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(domainData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const responseData = await response.json();

      // Update currentVersion from the response
      setCurrentVersion(responseData.version);
      console.log('Response data:', responseData);

      // Fetch the latest data
      await fetchData()

      setIsModified(false);
      alert('Graph saved successfully!');
    } catch (error) {
      console.error('Error saving graph:', error);
      alert('An error occurred while saving the graph.');
    }
  };

  return (
    <Box bg="gray.50" minH="100vh" py={10}>
      <Container maxW="container.xl">
        <Heading fontSize="3xl" mb={8} fontWeight="bold" color="gray.900" letterSpacing="tight">
          Explore Domain Concepts, Methodologies, and Sources
        </Heading>
        <Text fontSize="lg" color="gray.500" mb={4}>
          Current Version: {currentVersion} {isModified && '(Unsaved Changes)'}
        </Text>
        <Flex justify="center">
          <Box width="100%">
            {concepts.length > 0 || methodologies.length > 0 || sources.length > 0 ? (
              <Box height="500px" bg="white" borderRadius="xl" boxShadow="lg" p={5}>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesState}
                  onConnect={onConnect}
                  onNodeClick={onNodeClick}
                  onEdgeClick={onEdgeClick}
                  onPaneClick={() => {
                    setSelectedNode(null);
                    setSelectedEdge(null);
                  }}
                  fitView
                >
                  <Controls /> {/* Add zoom controls */}
                  <MiniMap pannable />   {/* Add mini-map */}
                </ReactFlow>
              </Box>
            ) : <Text fontSize="lg" color="gray.500">No data found for this domain.</Text>}
          </Box>
        </Flex>
        <Flex justify="center" mt={8}>
          <Button colorScheme="gray" size="lg" onClick={() => navigate(`/domains/${domain_id}/config`)}>
            Domain Settings
          </Button>
          <Button colorScheme="green" size="lg" ml={6} onClick={onOpen}>
            Add New Node
          </Button>
          <Button colorScheme="blue" size="lg" ml={6} onClick={onRelOpen}>
            Add Relationship
          </Button>
          <Button colorScheme="teal" size="lg" ml={6} onClick={saveGraph}>
            Save Graph
          </Button>
        </Flex>

        {/* Modal for adding new node */}
        <Modal isOpen={isOpen} onClose={onClose}>
          <ModalOverlay />
          <ModalContent borderRadius="xl" p={4}>
            <ModalHeader fontSize="2xl" fontWeight="bold" color="gray.900">Create a New Node</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Select
                placeholder="Select node type"
                value={newNodeType}
                onChange={(e) => setNewNodeType(e.target.value)}
                mb={4}
                size="lg"
              >
                <option value="concept">Concept</option>
                <option value="methodology">Methodology</option>
                <option value="source">Source</option>
              </Select>
              <Input
                placeholder="Node name"
                value={newNodeName}
                onChange={(e) => setNewNodeName(e.target.value)}
                mb={4}
                size="lg"
              />
              <Input
                placeholder="Node description"
                value={newNodeDescription}
                onChange={(e) => setNewNodeDescription(e.target.value)}
                mb={4}
                size="lg"
              />
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="green" size="lg" onClick={addNewNode}>
                Add Node
              </Button>
              <Button variant="ghost" onClick={onClose} size="lg">Cancel</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Modal for adding relationship */}
        <Modal isOpen={isRelOpen} onClose={onRelClose}>
          <ModalOverlay />
          <ModalContent borderRadius="xl" p={4}>
            <ModalHeader fontSize="2xl" fontWeight="bold" color="gray.900">Create a New Relationship</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Select placeholder="Select source node" value={selectedSourceNode} onChange={(e) => setSelectedSourceNode(e.target.value)} mb={4} size="lg">
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.data.label} ({node.data.type})
                  </option>
                ))}
              </Select>
              <Select placeholder="Select target node" value={selectedTargetNode} onChange={(e) => setSelectedTargetNode(e.target.value)} mb={4} size="lg">
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.data.label} ({node.data.type})
                  </option>
                ))}
              </Select>
              <Select placeholder="Select relationship type" value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)} mb={4} size="lg">
                <option value="depends_on">Depends On</option>
                <option value="related_to">Related To</option>
                <option value="part_of">Part Of</option>
              </Select>
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="blue" size="lg" onClick={addRelationship}>
                Add Relationship
              </Button>
              <Button variant="ghost" size="lg" onClick={onRelClose}>Cancel</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Modal for node information */}
        <Modal isOpen={isNodeModalOpen} onClose={() => setIsNodeModalOpen(false)}>
          <ModalOverlay />
          <ModalContent borderRadius="xl" p={4}>
            <ModalHeader fontSize="2xl" fontWeight="bold" color="gray.900">
              {selectedNode?.data.label}
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Text mt={4} color="gray.600">
                <b>Type:</b> {selectedNode?.data.type}
              </Text>
              <Text mt={2} color="gray.600">
                <b>Description:</b> {selectedNode?.data.description || 'No description available'}
              </Text>
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="red" onClick={removeNode}>Remove Node</Button>
              <Button variant="ghost" onClick={() => setIsNodeModalOpen(false)}>Close</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Modal for edge information */}
        <Modal isOpen={isEdgeModalOpen} onClose={() => setIsEdgeModalOpen(false)}>
          <ModalOverlay />
          <ModalContent borderRadius="xl" p={4}>
            <ModalHeader fontSize="2xl" fontWeight="bold" color="gray.900">Relationship</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Text mt={4} color="gray.600"><b>Source:</b> {selectedEdge?.sourceLabel}</Text>
              <Text mt={2} color="gray.600"><b>Target:</b> {selectedEdge?.targetLabel}</Text>
              <Text mt={2} color="gray.600"><b>Type:</b> {selectedEdge?.data?.relationship_type}</Text>
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="red" onClick={removeRelationship}>Remove Relationship</Button>
              <Button variant="ghost" onClick={() => setIsEdgeModalOpen(false)}>Close</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

      </Container>
    </Box>
  );
};

export default DomainPage;