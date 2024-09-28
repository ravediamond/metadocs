import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Heading, Container, Text, Input, Button, Flex, Stack } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const DomainConfigPage = () => {
  const { domain_id } = useParams();
  const { token } = useContext(AuthContext);
  const [config, setConfig] = useState([]);
  const [newConfig, setNewConfig] = useState({});

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/config`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const data = await response.json();
        if (response.ok) {
          setConfig(data);
        } else {
          console.error('Failed to fetch domain config');
        }
      } catch (error) {
        console.error('Error fetching domain config:', error);
      }
    };

    if (domain_id && token) {
      fetchConfig();
    }
  }, [domain_id, token]);

  const handleInputChange = (key, value) => {
    setNewConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    for (const key in newConfig) {
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/${domain_id}/config`, {
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
    <Box bg="gray.50" minH="100vh" py={12}>
      <Container maxW="container.xl">
        <Heading fontSize={{ base: '3xl', md: '4xl' }} fontWeight="bold" color="gray.800" mb={8}>
          Domain Configuration
        </Heading>

        {config.length > 0 ? (
          <Stack spacing={6}>
            {config.map((item) => (
              <Box
                key={item.config_id}
                p={6}
                border="1px solid"
                borderColor="gray.200"
                borderRadius="lg"
                bg="white"
                shadow="sm"
                _hover={{ shadow: 'md' }}
              >
                <Text fontSize="lg" mb={4} fontWeight="semibold" color="blue.600">
                  {item.config_key}
                </Text>
                <Text fontSize="md" color="gray.600" mb={4}>
                  Current Value: {item.config_value}
                </Text>
                <Input
                  size="lg"
                  placeholder={`Update ${item.config_key}`}
                  onChange={(e) => handleInputChange(item.config_key, e.target.value)}
                  bg="gray.50"
                  _focus={{ borderColor: 'blue.500' }}
                />
              </Box>
            ))}
          </Stack>
        ) : (
          <Text fontSize="lg" color="gray.600" textAlign="center">
            No configuration available for this domain.
          </Text>
        )}

        <Flex justify="center" mt={10}>
          <Button
            colorScheme="blue"
            size="lg"
            px={10}
            py={6}
            onClick={handleSubmit}
            shadow="md"
            _hover={{ bg: 'blue.600' }}
          >
            Save Config Changes
          </Button>
        </Flex>
      </Container>
    </Box>
  );
};

export default DomainConfigPage;