import React, { useState, useEffect, useContext } from 'react';
import { Box, Heading, Container, Text, Button, Flex, VStack, Input, useToast } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const UserConfigPage = () => {
  const { token } = useContext(AuthContext);
  const [apiKeys, setApiKeys] = useState([]);
  const [newKey, setNewKey] = useState(null);
  const [showNewKey, setShowNewKey] = useState(false); // Control visibility of new API key
  const toast = useToast();

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
    <Box bg="gray.50" minH="100vh" py={12} display="flex" justifyContent="center" alignItems="center">
      <Container maxW="container.lg" bg="white" p={10} borderRadius="lg" shadow="lg">
        <Heading as="h1" size="xl" fontWeight="bold" textAlign="center" mb={8} color="gray.800">
          API Key Management
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
            <Button colorScheme="blue" onClick={acknowledgeNewKey} size="lg" width="full">
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
      </Container>
    </Box>
  );
};

export default UserConfigPage;