import React, { useState, useEffect, useContext } from 'react';
import { Box, Heading, Container, Text, Input, Button, Flex } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const UserConfigPage = () => {
  const { token } = useContext(AuthContext);
  const [config, setConfig] = useState([]);
  const [newConfig, setNewConfig] = useState({});

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me/config`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const data = await response.json();
        if (response.ok) {
          setConfig(data);
        } else {
          console.error('Failed to fetch user config');
        }
      } catch (error) {
        console.error('Error fetching user config:', error);
      }
    };

    if (token) {
      fetchConfig();
    }
  }, [token]);

  const handleInputChange = (key, value) => {
    setNewConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    for (const key in newConfig) {
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me/config`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            config_key: key,
            config_value: newConfig[key],
          }),
        });

        if (!response.ok) {
          console.error('Failed to update config');
        }
      } catch (error) {
        console.error('Error updating config:', error);
      }
    }
    window.location.reload();
  };

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading fontSize="2xl" mb={6}>
          User Configuration
        </Heading>

        {config.length > 0 ? (
          config.map((item) => (
            <Box key={item.config_id} mb={4} p={4} bg="white" borderRadius="md" boxShadow="md">
              <Text mb={2}><b>{item.config_key}</b>: {item.config_value}</Text>
              <Input
                placeholder={`Update ${item.config_key}`}
                onChange={(e) => handleInputChange(item.config_key, e.target.value)}
              />
            </Box>
          ))
        ) : (
          <Text>No configuration available for this user.</Text>
        )}

        <Flex justify="center" mt={6}>
          <Button colorScheme="blue" onClick={handleSubmit}>Save Config Changes</Button>
        </Flex>
      </Container>
    </Box>
  );
};

export default UserConfigPage;