import React, { useState, useEffect, useContext } from 'react';
import { Box, Heading, Container, Text, Button, Flex, VStack, Input, useToast, Select } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const UserConfigPage = () => {
  const { token, currentTenant } = useContext(AuthContext);
  const [apiKeys, setApiKeys] = useState([]);
  const [newKey, setNewKey] = useState(null);
  const [showNewKey, setShowNewKey] = useState(false); // Control visibility of new API key
  const [invitations, setInvitations] = useState([]);  // Track existing invitations
  const [inviteeEmail, setInviteeEmail] = useState("");  // Track email input for invitation
  const [domainOptions, setDomainOptions] = useState([]);  // Available domains
  const [selectedDomain, setSelectedDomain] = useState("");  // Selected domain for invitation
  const toast = useToast();

  useEffect(() => {
    // Fetch API keys
    const fetchAPIKeys = async () => {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/config/tenants/${currentTenant}/me/api-keys`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setApiKeys(data);
      }
    };

    // Fetch domains for invitation dropdown
    const fetchDomains = async () => {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setDomainOptions(data);  // Populate domain options
      } else {
        toast({
          title: 'Error fetching domains.',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      }
    };

    // Fetch existing invitations
    const fetchInvitations = async () => {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/tenants/${currentTenant}/invitations`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setInvitations(data.filter(invite => invite.status === 'pending'));  // Only show pending invitations
      }
    };

    fetchAPIKeys();
    fetchDomains();
    fetchInvitations();
  }, [token]);

  const generateAPIKey = async () => {
    const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/config/tenants/${currentTenant}/me/api-keys`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    const data = await response.json();
    if (response.ok) {
      setNewKey(data.api_key);  // Store the new API key
      setShowNewKey(true);      // Show the key to the user
      setApiKeys([...apiKeys, data]);  // Add the new key to the list
    } else {
      toast({
        title: 'Error generating API key.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const revokeAPIKey = async (api_key_id) => {
    await fetch(`${process.env.REACT_APP_BACKEND_URL}/config/tenants/${currentTenant}/me/api-keys/${api_key_id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    setApiKeys(apiKeys.filter(key => key.api_key_id !== api_key_id));
  };

  const inviteUser = async () => {
    const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/tenants/${currentTenant}/invite`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        invitee_email: inviteeEmail,
        tenant_id: currentTenant,
        domain_id: selectedDomain || null,  // Optional domain
      }),
    });

    if (response.ok) {
      const newInvitation = await response.json();
      setInvitations([...invitations, newInvitation]);  // Add new invitation to list
      setInviteeEmail("");  // Clear the input field
      setSelectedDomain("");  // Reset domain selection
      toast({
        title: 'Invitation sent successfully!',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } else {
      toast({
        title: 'Error sending invitation.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <Box bg="gray.50" minH="100vh" py={12} display="flex" justifyContent="center" alignItems="center">
      <Container maxW="container.lg" bg="white" p={10} borderRadius="lg" shadow="lg">
        <Heading as="h1" size="xl" fontWeight="bold" textAlign="center" mb={8} color="gray.800">
          API Key & Invitation Management
        </Heading>

        {/* Display the newly generated API key */}
        {showNewKey && newKey && (
          <Box mb={6} p={6} bg="gray.100" borderRadius="md" shadow="md">
            <Text fontWeight="bold" fontSize="lg" mb={4} color="blue.600">
              Your new API Key:
            </Text>
            <Input value={newKey} isReadOnly size="lg" bg="white" mb={4} />
            <Text color="red.500" fontSize="sm" mb={6}>
              Please store this key securely. You won’t be able to view it again after closing this message.
            </Text>
            <Button colorScheme="blue" onClick={() => setShowNewKey(false)} size="lg" width="full">
              I have stored it
            </Button>
          </Box>
        )}

        {/* Button to generate a new API Key */}
        <Button
          colorScheme="blue"
          size="lg"
          onClick={generateAPIKey}
          mb={8}
          py={6}
          width="full"
          _hover={{ bg: 'blue.600' }}
        >
          Generate New API Key
        </Button>

        {/* List of existing API keys */}
        <VStack spacing={6} width="full">
          {apiKeys.map(key => (
            <Flex key={key.api_key_id} width="full" justify="space-between" p={4} bg="gray.50" boxShadow="sm" borderRadius="md">
              <Text fontSize="md" color="gray.700">
                Key Created: {new Date(key.created_at).toLocaleString()}
              </Text>
              <Button colorScheme="red" size="sm" onClick={() => revokeAPIKey(key.api_key_id)}>
                Revoke
              </Button>
            </Flex>
          ))}
        </VStack>

        <Box mt={12}>
          <Heading as="h2" size="lg" fontWeight="bold" textAlign="center" mb={6} color="gray.800">
            Send an Invitation
          </Heading>
          <VStack spacing={4} align="stretch">
            <Input
              placeholder="Invitee's email"
              value={inviteeEmail}
              onChange={(e) => setInviteeEmail(e.target.value)}
              size="lg"
              bg="white"
            />
            <Select placeholder="Select Domain (optional)" size="lg" value={selectedDomain} onChange={(e) => setSelectedDomain(e.target.value)}>
              {domainOptions.map(domain => (
                <option key={domain.domain_id} value={domain.domain_id}>
                  {domain.domain_name}
                </option>
              ))}
            </Select>
            <Button colorScheme="blue" size="lg" onClick={inviteUser}>
              Send Invitation
            </Button>
          </VStack>
        </Box>

        {/* List of existing invitations */}
        <Box mt={12}>
          <Heading as="h2" size="lg" fontWeight="bold" textAlign="center" mb={6} color="gray.800">
            Pending Invitations
          </Heading>
          <VStack spacing={6} width="full">
            {invitations.map(invitation => (
              <Flex key={invitation.invitation_id} width="full" justify="space-between" p={4} bg="gray.50" boxShadow="sm" borderRadius="md">
                <Text fontSize="md" color="gray.700">
                  Invitation to: {invitation.invitee_email} - Status: {invitation.status}
                </Text>
              </Flex>
            ))}
          </VStack>
        </Box>
      </Container>
    </Box>
  );
};

export default UserConfigPage;