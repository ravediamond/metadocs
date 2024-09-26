import React, { useState, useEffect, useContext } from 'react';
import { Box, Heading, Container, Text, Button, Flex, VStack, Input } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const UserConfigPage = () => {
  const { token } = useContext(AuthContext);
  const [apiKeys, setApiKeys] = useState([]);
  const [newKey, setNewKey] = useState(null);
  const [showNewKey, setShowNewKey] = useState(false); // Control visibility of new API key

  useEffect(() => {
    // Fetch API keys
    const fetchAPIKeys = async () => {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me/api-keys`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setApiKeys(data);
      }
    };

    fetchAPIKeys();
  }, [token]);

  const generateAPIKey = async () => {
    const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me/api-keys`, {
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
    }
  };

  const revokeAPIKey = async (api_key_id) => {
    await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me/api-keys/${api_key_id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    setApiKeys(apiKeys.filter(key => key.api_key_id !== api_key_id));
  };

  // Acknowledge button click - hide the new API key after acknowledgment
  const acknowledgeNewKey = () => {
    setShowNewKey(false);
    setNewKey(null); // Clear the key after acknowledgment
  };

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading fontSize="2xl" mb={6}>
          API Key Management
        </Heading>

        {/* Display the newly generated API key */}
        {showNewKey && newKey && (
          <Box mb={4} p={4} bg="white" boxShadow="md" borderRadius="md">
            <Text fontWeight="bold" mb={2}>Your new API Key:</Text>
            <Input value={newKey} isReadOnly mb={4} />
            <Text color="red.500" fontSize="sm" mb={4}>
              Please store this key securely. You won't be able to view it again after you close this message.
            </Text>
            <Button colorScheme="blue" onClick={acknowledgeNewKey}>
              Okay, I have stored it
            </Button>
          </Box>
        )}

        {/* Button to generate a new API Key */}
        <Button colorScheme="blue" onClick={generateAPIKey} mb={6}>
          Generate New API Key
        </Button>

        {/* List of existing API keys */}
        <VStack spacing={4}>
          {apiKeys.map(key => (
            <Flex key={key.api_key_id} width="100%" justify="space-between" p={4} bg="white" boxShadow="sm" borderRadius="md">
              <Text>Key Created: {new Date(key.created_at).toLocaleString()}</Text>
              <Button colorScheme="red" size="sm" onClick={() => revokeAPIKey(key.api_key_id)}>
                Revoke
              </Button>
            </Flex>
          ))}
        </VStack>
      </Container>
    </Box>
  );
};

export default UserConfigPage;