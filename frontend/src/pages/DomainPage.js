// DomainPage.jsx

import React, { useEffect, useState, useContext } from 'react';
import {
  Box, Heading, Container, Text, Flex, Button, Select, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalFooter, ModalBody, ModalCloseButton, Input, useDisclosure
} from '@chakra-ui/react';
import { ReactFlow, addEdge, useNodesState, useEdgesState } from '@xyflow/react';
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
  const { token } = useContext(AuthContext);
  const navigate = useNavigate();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isRelOpen, onOpen: onRelOpen, onClose: onRelClose } = useDisclosure();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [newNodeType, setNewNodeType] = useState('concept');
  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeDescription, setNewNodeDescription] = useState('');
  const [selectedSourceNode, setSelectedSourceNode] = useState('');
  const [selectedTargetNode, setSelectedTargetNode] = useState('');
  const [relationshipType, setRelationshipType] = useState('');
  const [currentVersion, setCurrentVersion] = useState(1);
  const [isModified, setIsModified] = useState(false);

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
            }
          : null
      )
      .filter(Boolean);

    // Layout the nodes using dagre
    const layoutedNodes = getLayoutedNodes(allNodes, relationshipEdges);
    setNodes(layoutedNodes);
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

  const fetchData = async () => {
    if (!token) return;

    try {
      const [conceptsRes, methodologiesRes, sourcesRes, domainRes] = await Promise.all([
        fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/concepts`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/methodologies`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/sources`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/details`, { headers: { Authorization: `Bearer ${token}` } })
      ]);

      const [conceptsData, methodologiesData, sourcesData, domainData] = await Promise.all([conceptsRes.json(), methodologiesRes.json(), sourcesRes.json(), domainRes.json()]);

      if (conceptsRes.ok && methodologiesRes.ok && sourcesRes.ok) {
        setConcepts(conceptsData);
        setMethodologies(methodologiesData);
        setSources(sourcesData);
        console.log('Domain Data:', domainData);
        setCurrentVersion(domainData.version);

        const relationships = await fetchRelationships();
        generateFlowElements(conceptsData, methodologiesData, sourcesData, relationships);
      }
    } catch {}
  };

  useEffect(() => {

    if (domain_id) fetchData();
  }, [domain_id, token]);

  const onConnect = (params) => {
    const newEdge = addEdge(params, edges);
    setEdges(newEdge);
    setIsModified(true);
  };

  const onNodeClick = (_, node) => {
    setSelectedNode(node);
    setSelectedSourceNode(node.id);
  };

  const onEdgeClick = (_, edge) => {
    const sourceLabel = nodes.find(node => node.id === edge.source)?.data.label;
    const targetLabel = nodes.find(node => node.id === edge.target)?.data.label;

    setSelectedEdge({
      ...edge,
      sourceLabel,
      targetLabel,
    });
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
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/${endpoint}/${nodeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error('Error:', error);
    }

    setSelectedNode(null);
  };

  // Function to remove a relationship
  const removeRelationship = async () => {
    if (!selectedEdge) return;

    const edgeId = selectedEdge.id;

    const updatedEdges = edges.filter((edge) => edge.id !== edgeId);

    setEdges(updatedEdges);
    setIsModified(true);

    try {
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/relationships/${edgeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error('Error:', error);
    }

    setSelectedEdge(null);
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
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/save`, {
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

  // Helper function to update local entities with IDs from the server response
  const updateLocalEntities = (responseData) => {
    // Update Concepts
    const updatedConcepts = responseData.concepts;
    setNodes((nds) =>
      nds.map((node) => {
        if (node.data.type === 'concept') {
          const updatedConcept = updatedConcepts.find(c => c.name === node.data.label);
          if (updatedConcept && node.id !== updatedConcept.concept_id) {
            node.id = updatedConcept.concept_id;
            node.data.id = updatedConcept.concept_id;
            node.data.domain_version = updatedConcept.domain_version; // Update domain_version
          }
        }
        return node;
      })
    );

    // Update Sources
    const updatedSources = responseData.sources;
    setNodes((nds) =>
      nds.map((node) => {
        if (node.data.type === 'source') {
          const updatedSource = updatedSources.find(s => s.name === node.data.label);
          if (updatedSource && node.id !== updatedSource.source_id) {
            node.id = updatedSource.source_id;
            node.data.id = updatedSource.source_id;
            node.data.domain_version = updatedSource.domain_version; // Update domain_version
          }
        }
        return node;
      })
    );

    // Update Methodologies
    const updatedMethodologies = responseData.methodologies;
    setNodes((nds) =>
      nds.map((node) => {
        if (node.data.type === 'methodology') {
          const updatedMethodology = updatedMethodologies.find(m => m.name === node.data.label);
          if (updatedMethodology && node.id !== updatedMethodology.methodology_id) {
            node.id = updatedMethodology.methodology_id;
            node.data.id = updatedMethodology.methodology_id;
            node.data.domain_version = updatedMethodology.domain_version; // Update domain_version
          }
        }
        return node;
      })
    );

    // Update Relationships
    const updatedRelationships = responseData.relationships;
    setEdges((eds) =>
      eds.map((edge) => {
        const updatedRelationship = updatedRelationships.find(r =>
          r.entity_id_1 === edge.source &&
          r.entity_id_2 === edge.target &&
          r.relationship_type === edge.data.relationship_type
        );
        if (updatedRelationship && edge.id !== updatedRelationship.relationship_id) {
          edge.id = updatedRelationship.relationship_id;
          edge.data.id = updatedRelationship.relationship_id;
          edge.data.domain_version = updatedRelationship.domain_version; // Update domain_version
        }
        return edge;
      })
    );
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
        <Flex justify="space-between">
          <Box width="70%">
            {concepts.length > 0 || methodologies.length > 0 || sources.length > 0 ? (
              <Box height="500px" bg="white" borderRadius="xl" boxShadow="lg" p={5}>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={onNodeClick}
                  onEdgeClick={onEdgeClick}
                  fitView
                />
              </Box>
            ) : <Text fontSize="lg" color="gray.500">No data found for this domain.</Text>}
          </Box>
          <Box width="25%" p={6} bg="white" borderRadius="xl" boxShadow="lg">
            {selectedNode ? (
              <>
                <Heading size="lg" color="gray.900">{selectedNode.data.label}</Heading>
                <Text mt={4} color="gray.600"><b>Type:</b> {selectedNode.data.type}</Text>
                <Text mt={2} color="gray.600"><b>Description:</b> {selectedNode.data.description || 'No description available'}</Text>
                <Button colorScheme="red" mt={4} onClick={removeNode}>Remove Node</Button>
              </>
            ) : selectedEdge ? (
              <>
                <Heading size="lg" color="gray.900">Relationship</Heading>
                <Text mt={4} color="gray.600"><b>Source:</b> {selectedEdge.sourceLabel}</Text>
                <Text mt={2} color="gray.600"><b>Target:</b> {selectedEdge.targetLabel}</Text>
                <Text mt={2} color="gray.600"><b>Type:</b> {selectedEdge.data?.relationship_type}</Text>
                <Button colorScheme="red" mt={4} onClick={removeRelationship}>Remove Relationship</Button>
              </>
            ) : (
              <Text fontSize="lg" color="gray.500">Select a node or relationship to see details</Text>
            )}
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
      </Container>
    </Box>
  );
};

export default DomainPage;