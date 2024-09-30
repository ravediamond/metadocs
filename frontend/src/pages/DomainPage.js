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
  const [selectedEdge, setSelectedEdge] = useState(null);  // To track selected edge
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
  const [currentVersion, setCurrentVersion] = useState(1);  // Add a state for version tracking
  const [isModified, setIsModified] = useState(false);  // To track if graph has been modified

  const generateFlowElements = (concepts, methodologies, sources, relationships) => {
    const typeColors = {
      concept: '#FFB6C1', methodology: '#90EE90', source: '#FFD700', other: '#FFA07A',
    };

    // Create a map of node IDs to their labels for easy lookup
    const nodeLabelMap = {};

    const createNode = (item, type) => {
      const nodeId = item[`${type}_id`];
      
      // Populate the nodeLabelMap with node IDs and their corresponding labels
      nodeLabelMap[nodeId] = item.name;

      return {
        id: nodeId,
        data: { label: item.name, type, description: item.description },
        style: {
          background: typeColors[type] || typeColors.other,
          borderRadius: '12px',
          padding: '15px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        },
        width: nodeWidth,
        height: nodeHeight,
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
      .map(({ entity_id_1: source, entity_id_2: target, relationship_type }) => 
        allNodes.some((n) => n.id === source) && allNodes.some((n) => n.id === target)
          ? { 
              id: `e${source}-${target}`, 
              source, 
              target, 
              animated: true, 
              style: { stroke: '#4682B4', strokeWidth: 2 },
              data: { relationship_type },  // Store relationship type in edge data
            }
          : null
      )
      .filter(Boolean);

    // Layout the nodes and edges using dagre
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
          setCurrentVersion(domainData.version);
          console.log(domainData);

          const relationships = await fetchRelationships();
          generateFlowElements(conceptsData, methodologiesData, sourcesData, relationships);
        }
      } catch {}
    };

    if (domain_id) fetchData();
  }, [domain_id, token]);

  const onConnect = (params) => setEdges((eds) => addEdge(params, eds));
  const onNodeClick = (_, node) => setSelectedNode(node);
  
  // Modify the onEdgeClick function to use the node labels instead of just IDs
  const onEdgeClick = (_, edge) => {
    const sourceLabel = nodes.find(node => node.id === edge.source)?.data.label;
    const targetLabel = nodes.find(node => node.id === edge.target)?.data.label;

    setSelectedEdge({
      ...edge,
      sourceLabel,  // Store the source label
      targetLabel,  // Store the target label
    });
  };

  // Function to add a new node
  const addNewNode = async () => {
    if (!newNodeName || !newNodeDescription) {
      alert('Please provide a name and description for the node');
      return;
    }
  
    const newNodeId = `new_node_${nodes.length + 1}`;
    const newNode = {
      id: newNodeId,
      data: { label: newNodeName, type: newNodeType, description: newNodeDescription },
      position: { x: Math.random() * 300, y: Math.random() * 300 },
      style: {
        background: newNodeType === 'concept' ? '#FFB6C1' : newNodeType === 'methodology' ? '#90EE90' : '#FFD700',
        borderRadius: '12px',
        padding: '15px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
      },
      width: nodeWidth,
      height: nodeHeight,
    };
  
    setNodes((nds) => [...nds, newNode]);
    setIsModified(true);  // Set as modified
  
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/nodes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ label: newNodeName, description: newNodeDescription, type: newNodeType }),
      });
      if (!response.ok) throw new Error('Failed to register the new node.');
    } catch (error) {
      console.error('Error:', error);
    }
  
    onClose();
    setNewNodeName('');
    setNewNodeDescription('');
  };

  // Function to remove a node and its relationships
  const removeNode = async () => {
    if (!selectedNode) return;

    const nodeId = selectedNode.id;

    // Remove the node from the front end
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)); // Remove related edges

    try {
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/nodes/${nodeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error('Error:', error);
    }

    setSelectedNode(null); // Clear selection
  };

  // Function to remove a relationship
  const removeRelationship = async () => {
    if (!selectedEdge) return;

    const edgeId = selectedEdge.id;

    // Remove the edge from the front end
    setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));

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

    setSelectedEdge(null); // Clear selection
  };

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

    onRelClose();
  };

  const saveGraph = async () => {
    try {
      // Split nodes by type
      const concepts = nodes.filter(node => node.data.type === 'concept');
      const sources = nodes.filter(node => node.data.type === 'source');
      const methodologies = nodes.filter(node => node.data.type === 'methodology');
  
      // Prepare the relationships (edges)
      const relationships = edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        relationship_type: edge.data.relationship_type,
      }));
  
      const newVersion = currentVersion + 1;  // Increment version number
  
      // Send concepts to /concepts endpoint
      if (concepts.length > 0) {
        const conceptData = concepts.map(concept => ({
          id: concept.id,
          label: concept.data.label,
          position: concept.position,
          description: concept.data.description,
          version: newVersion,  // Add version
        }));
        await fetch(`${process.env.REACT_APP_BACKEND_URL}/${domain_id}/concepts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(conceptData),
        });
      }
  
      // Send sources to /sources endpoint
      if (sources.length > 0) {
        const sourceData = sources.map(source => ({
          id: source.id,
          label: source.data.label,
          position: source.position,
          description: source.data.description,
          version: newVersion,  // Add version
        }));
        await fetch(`${process.env.REACT_APP_BACKEND_URL}/${domain_id}/sources`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(sourceData),
        });
      }
  
      // Send methodologies to /methodologies endpoint
      if (methodologies.length > 0) {
        const methodologyData = methodologies.map(methodology => ({
          id: methodology.id,
          label: methodology.data.label,
          position: methodology.position,
          description: methodology.data.description,
          version: newVersion,  // Add version
        }));
        await fetch(`${process.env.REACT_APP_BACKEND_URL}/${domain_id}/methodologies`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(methodologyData),
        });
      }
  
      // Send relationships (edges) to /relationships endpoint
      if (relationships.length > 0) {
        await fetch(`${process.env.REACT_APP_BACKEND_URL}/relationships`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(relationships),
        });
      }
  
      // Increment the domain version
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/version`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ version: newVersion }),
      });
  
      setCurrentVersion(newVersion);  // Update the current version
      setIsModified(false);  // Reset modification status
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
                  onEdgeClick={onEdgeClick}  // Track edge clicks
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
                <Button colorScheme="red" mt={4} onClick={removeNode}>Remove Node</Button> {/* Button to remove node */}
              </>
            ) : selectedEdge ? (
              <>
                <Heading size="lg" color="gray.900">Relationship</Heading>
                <Text mt={4} color="gray.600"><b>Source:</b> {selectedEdge.sourceLabel}</Text> {/* Display source label */}
                <Text mt={2} color="gray.600"><b>Target:</b> {selectedEdge.targetLabel}</Text> {/* Display target label */}
                <Text mt={2} color="gray.600"><b>Type:</b> {selectedEdge.data?.relationship_type}</Text>  {/* Display relationship type */}
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