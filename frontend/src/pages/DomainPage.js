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
import { v4 as uuidv4 } from 'uuid';

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
  const [entities, setEntities] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const { token, currentTenant } = useContext(AuthContext);
  const navigate = useNavigate();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isRelOpen, onOpen: onRelOpen, onClose: onRelClose } = useDisclosure();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesState] = useEdgesState([]);
  const [newNodeType, setNewNodeType] = useState('Department');
  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeDescription, setNewNodeDescription] = useState('');
  const [selectedSourceNode, setSelectedSourceNode] = useState('');
  const [selectedTargetNode, setSelectedTargetNode] = useState('');
  const [relationshipType, setRelationshipType] = useState('');
  const [currentVersion, setCurrentVersion] = useState(1);
  const [isModified, setIsModified] = useState(false);

  const generateFlowElements = (entities, relationships) => {
    const typeColors = {
      Department: '#FFB6C1', System: '#90EE90', Service: '#FFD700', other: '#FFA07A',
    };

    relationships.forEach(({ from_entity_id, to_entity_id }) => {
      const sourceExists = entities.find(e => e.id === from_entity_id);
      const targetExists = entities.find(e => e.id === to_entity_id);
      if (!sourceExists || !targetExists) {
        console.warn(`Invalid relationship: ${from_entity_id} to ${to_entity_id}`);
      }
    });

    const createNode = (entity) => {
      return {
        id: entity.id,
        data: {
          label: entity.name,
          type: entity.type,
          description: entity.description,
          metadata: entity.metadata,
          vector: entity.vector,
          created_at: entity.created_at,
        },
        style: {
          background: typeColors[entity.type] || typeColors.other,
          borderRadius: '12px',
          padding: '15px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        },
        width: nodeWidth,
        height: nodeHeight,
        position: { x: 0, y: 0 },
      };
    };

    const allNodes = entities.map((e) => createNode(e));

    const relationshipEdges = relationships.map(({ id, name, type, description, from_entity_id, to_entity_id }) => {
      const edge = {
        id: id,
        source: from_entity_id,
        target: to_entity_id,
        type: 'default',
        animated: true,
        style: { stroke: '#4682B4', strokeWidth: 2 },
        data: { name, type, description },
        label: name,
        labelStyle: { fill: '#4682B4', fontWeight: 700 },
      };
      return edge;
    });

    const layoutedNodes = getLayoutedNodes(allNodes, relationshipEdges);
    setNodes(layoutedNodes);
    setEdges(relationshipEdges);
  };

  const fetchData = async () => {
    if (!token) return;

    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const domainData = await res.json();
        const { entities, relationships, version } = domainData;
        setEntities(entities);
        setRelationships(relationships);
        setCurrentVersion(version);

        generateFlowElements(entities, relationships);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    }
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
  };

  const addNewEntity = () => {
    if (!newNodeName || !newNodeDescription) {
      alert('Please provide a name and description for the entity');
      return;
    };

    const now = new Date().toISOString();

    const newEntity = {
      id: uuidv4(),
      name: newNodeName,
      type: newNodeType,
      description: newNodeDescription,
      metadata: '{}',
      vector: [0.0, 0.0, 0.0, 0.0],
      created_at: now,
    };

    const updatedEntities = [...entities, newEntity];
    setEntities(updatedEntities);

    const newNode = {
      id: newEntity.id,
      data: {
        label: newEntity.name,
        type: newEntity.type,
        description: newEntity.description,
        metadata: newEntity.metadata,
        vector: newEntity.vector,
        created_at: newEntity.created_at,
      },
      style: {
        background: {
          Department: '#FFB6C1',
          System: '#90EE90',
          Service: '#FFD700',
          other: '#FFA07A',
        }[newEntity.type] || '#FFA07A',
        borderRadius: '12px',
        padding: '15px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
      },
      width: nodeWidth,
      height: nodeHeight,
      position: { x: Math.random() * 400, y: Math.random() * 400 },
    };

    setNodes([...nodes, newNode]);
    setIsModified(true);

    onClose();
    setNewNodeName('');
    setNewNodeDescription('');
  };

  const removeEntity = () => {
    if (!selectedNode) return;

    const entityId = selectedNode.id;
    const updatedEntities = entities.filter((entity) => entity.id !== entityId);
    const updatedEdges = edges.filter((edge) => edge.source !== entityId && edge.target !== entityId);

    setEntities(updatedEntities);
    setNodes(nodes.filter((node) => node.id !== entityId));
    setEdges(updatedEdges);
    setIsModified(true);
    setSelectedNode(null);
  };

  const addRelationship = () => {
    if (!selectedSourceNode || !selectedTargetNode || !relationshipType) return;

    const newEdge = {
      id: uuidv4(),
      source: selectedSourceNode,
      target: selectedTargetNode,
      animated: true,
      style: { stroke: '#4682B4', strokeWidth: 2 },
      data: { name: relationshipType, type: 'Dependency', description: '' },
      label: relationshipType,
      labelStyle: { fill: '#4682B4', fontWeight: 700 },
    };

    setEdges([...edges, newEdge]);
    setIsModified(true);
    onRelClose();
  };

  const removeRelationship = () => {
    if (!selectedEdge) return;

    const edgeId = selectedEdge.id;
    const updatedEdges = edges.filter((edge) => edge.id !== edgeId);

    setEdges(updatedEdges);
    setIsModified(true);
    setSelectedEdge(null);
  };

  const saveGraph = async () => {
    try {
      const now = new Date().toISOString();

      const entitiesData = nodes.map(node => ({
        id: node.id,
        name: node.data.label,
        type: node.data.type,
        description: node.data.description,
        metadata: node.data.metadata,
        vector: node.data.vector,
        created_at: node.data.created_at,
      }));

      const relationshipsData = edges.map(edge => ({
        id: edge.id,
        name: edge.data.name,
        type: edge.data.type,
        description: edge.data.description,
        from_entity_id: edge.source,
        to_entity_id: edge.target,
        created_at: now,
      }));

      const domainData = {
        entities: entitiesData,
        relationships: relationshipsData,
      };

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
      setCurrentVersion(responseData.version);

      await fetchData();

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
          Explore Domain Entities and Relationships
        </Heading>
        <Text fontSize="lg" color="gray.500" mb={4}>
          Current Version: {currentVersion} {isModified && '(Unsaved Changes)'}
        </Text>
        <Flex>
          <Box width="70%" pr={4}>
            {entities.length > 0 || relationships.length > 0 ? (
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
                  <Controls />
                  <MiniMap pannable />
                </ReactFlow>
              </Box>
            ) : <Text fontSize="lg" color="gray.500">No data found for this domain.</Text>}
          </Box>
          <Box width="30%" pl={4}>
            {selectedNode && (
              <Box bg="white" borderRadius="xl" boxShadow="lg" p={5}>
                <Heading fontSize="2xl" fontWeight="bold" color="gray.900">
                  {selectedNode.data.label}
                </Heading>
                <Text mt={4} color="gray.600">
                  <b>Type:</b> {selectedNode.data.type}
                </Text>
                <Text mt={2} color="gray.600">
                  <b>Description:</b> {selectedNode.data.description || 'No description available'}
                </Text>
                <Button mt={4} colorScheme="red" onClick={removeEntity}>Remove Entity</Button>
              </Box>
            )}
            {selectedEdge && (
              <Box bg="white" borderRadius="xl" boxShadow="lg" p={5}>
                <Heading fontSize="2xl" fontWeight="bold" color="gray.900">
                {selectedEdge.data.name}
                </Heading>
                <Text mt={4} color="gray.600"><b>Source:</b> {selectedEdge.sourceLabel}</Text>
                <Text mt={2} color="gray.600"><b>Target:</b> {selectedEdge.targetLabel}</Text>
                <Text mt={2} color="gray.600"><b>Type:</b> {selectedEdge.data.type}</Text>
                <Text mt={2} color="gray.600">
                  <b>Description:</b> {selectedEdge.data.description || 'No description available'}
                </Text>
                <Button mt={4} colorScheme="red" onClick={removeRelationship}>Remove Relationship</Button>
              </Box>
            )}
            {(!selectedNode && !selectedEdge) && (
              <Text fontSize="lg" color="gray.500">Select an entity or relationship to see details.</Text>
            )}
          </Box>
        </Flex>
        <Flex justify="center" mt={8}>
          <Button colorScheme="gray" size="lg" onClick={() => navigate(`/domains/${domain_id}/config`)}>
            Domain Settings
          </Button>
          <Button colorScheme="green" size="lg" ml={6} onClick={onOpen}>
            Add New Entity
          </Button>
          <Button colorScheme="blue" size="lg" ml={6} onClick={onRelOpen}>
            Add Relationship
          </Button>
          <Button colorScheme="teal" size="lg" ml={6} onClick={saveGraph}>
            Save Graph
          </Button>
          <Button
            colorScheme="purple"
            size="lg"
            ml={6}
            mt={2}
            onClick={() => navigate(`/domain/${domain_id}/upload`)}
          >
            Upload Files
          </Button>
        </Flex>

        {/* Modal for adding new entity */}
        <Modal isOpen={isOpen} onClose={onClose}>
          <ModalOverlay />
          <ModalContent borderRadius="xl" p={4}>
            <ModalHeader fontSize="2xl" fontWeight="bold" color="gray.900">Create a New Entity</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Select
                placeholder="Select entity type"
                value={newNodeType}
                onChange={(e) => setNewNodeType(e.target.value)}
                mb={4}
                size="lg"
              >
                <option value="Department">Department</option>
                <option value="System">System</option>
                <option value="Service">Service</option>
              </Select>
              <Input
                placeholder="Entity name"
                value={newNodeName}
                onChange={(e) => setNewNodeName(e.target.value)}
                mb={4}
                size="lg"
              />
              <Input
                placeholder="Entity description"
                value={newNodeDescription}
                onChange={(e) => setNewNodeDescription(e.target.value)}
                mb={4}
                size="lg"
              />
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="green" size="lg" onClick={addNewEntity}>
                Add Entity
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
              <Select placeholder="Select source entity" value={selectedSourceNode} onChange={(e) => setSelectedSourceNode(e.target.value)} mb={4} size="lg">
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.data.label} ({node.data.type})
                  </option>
                ))}
              </Select>
              <Select placeholder="Select target entity" value={selectedTargetNode} onChange={(e) => setSelectedTargetNode(e.target.value)} mb={4} size="lg">
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.data.label} ({node.data.type})
                  </option>
                ))}
              </Select>
              <Select placeholder="Select relationship type" value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)} mb={4} size="lg">
                <option value="Depends_On">Depends On</option>
                <option value="Part_Of">Part Of</option>
                <option value="Related_To">Related To</option>
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