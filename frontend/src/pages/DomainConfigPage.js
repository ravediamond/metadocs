import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Heading,
  Container,
  Text,
  Input,
  Button,
  Flex,
  Stack,
  Select,
  Alert,
  AlertIcon,
  Divider,
  FormControl,
  FormLabel,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Grid,
  GridItem,
} from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const LLMConfigSection = ({ config, onConfigChange, isLoading }) => {
  const provider = config?.llm_provider || 'bedrock';

  return (
    <Box mt={8}>
      <Heading size="lg" mb={6}>LLM Configuration</Heading>
      <Text color="gray.600" mb={4}>Configure your LLM Model settings here.</Text>

      <Grid templateColumns="repeat(2, 1fr)" gap={6}>
        <GridItem>
          <FormControl>
            <FormLabel>LLM Provider</FormLabel>
            <Select
              value={provider}
              onChange={(e) => onConfigChange('llm_provider', e.target.value)}
              isDisabled={isLoading}
            >
              <option value="bedrock">AWS Bedrock</option>
              <option value="anthropic">Anthropic</option>
            </Select>
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>Model ID</FormLabel>
            <Input
              value={config?.aws_model_id || ''}
              onChange={(e) => onConfigChange('aws_model_id', e.target.value)}
              placeholder="Enter model ID"
              isDisabled={isLoading}
            />
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>Temperature</FormLabel>
            <NumberInput
              min={0}
              max={1}
              step={0.1}
              value={config?.llm_temperature || 0}
              onChange={(value) => onConfigChange('llm_temperature', value)}
              isDisabled={isLoading}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>Max Tokens</FormLabel>
            <NumberInput
              min={1}
              max={100000}
              step={1}
              value={config?.llm_max_tokens || 1000}
              onChange={(value) => onConfigChange('llm_max_tokens', value)}
              isDisabled={isLoading}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        </GridItem>

        {provider === 'bedrock' && (
          <>
            <GridItem>
              <FormControl>
                <FormLabel>AWS Region</FormLabel>
                <Input
                  value={config?.aws_region || ''}
                  onChange={(e) => onConfigChange('aws_region', e.target.value)}
                  placeholder="Enter AWS region"
                  isDisabled={isLoading}
                />
              </FormControl>
            </GridItem>

            <GridItem>
              <FormControl>
                <FormLabel>AWS Profile</FormLabel>
                <Input
                  value={config?.aws_profile || ''}
                  onChange={(e) => onConfigChange('aws_profile', e.target.value)}
                  placeholder="Enter AWS profile name (optional)"
                  isDisabled={isLoading}
                />
              </FormControl>
            </GridItem>
          </>
        )}

        {provider === 'anthropic' && (
          <GridItem>
            <FormControl>
              <FormLabel>Anthropic API Key</FormLabel>
              <Input
                type="password"
                value={config?.anthropic_api_key || ''}
                onChange={(e) => onConfigChange('anthropic_api_key', e.target.value)}
                placeholder="Enter Anthropic API key"
                isDisabled={isLoading}
              />
            </FormControl>
          </GridItem>
        )}
      </Grid>
    </Box>
  );
};

const ProcessingConfigSection = ({ config, onConfigChange, isLoading }) => {
  return (
    <Box mt={8}>
      <Heading size="lg" mb={6}>Processing Configuration</Heading>
      <Text color="gray.600" mb={4}>These are domain-wide processing settings.</Text>

      <Grid templateColumns="repeat(2, 1fr)" gap={6}>
        <GridItem>
          <FormControl>
            <FormLabel>Processing Directory</FormLabel>
            <Input
              value={config?.processing_dir || ''}
              onChange={(e) => onConfigChange('processing_dir', e.target.value)}
              placeholder="Enter processing directory"
              isDisabled={isLoading}
            />
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>PDF Quality Threshold</FormLabel>
            <NumberInput
              value={config?.pdf_quality_threshold || 0}
              onChange={(value) => onConfigChange('pdf_quality_threshold', value)}
              isDisabled={isLoading}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>PDF Max Iterations</FormLabel>
            <NumberInput
              value={config?.pdf_max_iterations || 0}
              onChange={(value) => onConfigChange('pdf_max_iterations', value)}
              isDisabled={isLoading}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>Entity Max Iterations</FormLabel>
            <NumberInput
              value={config?.entity_max_iterations || 0}
              onChange={(value) => onConfigChange('entity_max_iterations', value)}
              isDisabled={isLoading}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        </GridItem>

        <GridItem>
          <FormControl>
            <FormLabel>Entity Batch Size</FormLabel>
            <NumberInput
              value={config?.entity_batch_size || 0}
              onChange={(value) => onConfigChange('entity_batch_size', value)}
              isDisabled={isLoading}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        </GridItem>
      </Grid>
    </Box>
  );
};

const DomainConfigPage = () => {
  const { domain_id } = useParams();
  const { token, currentTenant, currentUserRole } = useContext(AuthContext);
  const [config, setConfig] = useState({});
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedRoles, setSelectedRoles] = useState({});
  const [message, setMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch domain configuration
  const fetchConfig = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/config/tenants/${currentTenant}/domains/${domain_id}/config`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      if (response.ok) {
        // Transform array of configs into an object
        const configObj = data.reduce((acc, item) => {
          acc[item.config_key] = item.config_value;
          return acc;
        }, {});
        setConfig(configObj);
      } else {
        setMessage({ type: 'error', text: 'Failed to fetch domain config' });
      }
    } catch (error) {
      console.error('Error fetching domain config:', error);
      setMessage({ type: 'error', text: 'Error loading configuration' });
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch users in the domain
  const fetchUsers = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/users/tenants/${currentTenant}/domains/${domain_id}/users`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      if (response.ok) {
        setUsers(data);
      } else {
        console.error('Failed to fetch users');
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  // Fetch available roles
  const fetchRoles = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/roles/tenants/${currentTenant}/roles`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      if (response.ok) {
        setRoles(data);
      } else {
        console.error('Failed to fetch roles');
      }
    } catch (error) {
      console.error('Error fetching roles:', error);
    }
  };

  useEffect(() => {
    if (domain_id && token) {
      fetchConfig();
      fetchUsers();
      fetchRoles();
    }
  }, [domain_id, token]);

  const handleInputChange = (key, value) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      const responses = await Promise.all(
        Object.entries(config).map(([key, value]) =>
          fetch(
            `${process.env.REACT_APP_BACKEND_URL}/config/tenants/${currentTenant}/domains/${domain_id}/config?config_key=${encodeURIComponent(key)}&config_value=${encodeURIComponent(value.toString())}`,
            {
              method: 'PUT',
              headers: {
                Authorization: `Bearer ${token}`,
              }
            }
          )
        )
      );

      if (responses.every(response => response.ok)) {
        setMessage({ type: 'success', text: 'Configuration updated successfully' });
        fetchConfig();
      } else {
        setMessage({ type: 'error', text: 'Failed to update some configuration values' });
      }
    } catch (error) {
      console.error('Error updating config:', error);
      setMessage({ type: 'error', text: 'Error saving configuration' });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle role selection change
  const handleRoleChange = (userId, roleName) => {
    setSelectedRoles((prev) => ({
      ...prev,
      [userId]: roleName,
    }));
  };

  // Assign role to a user
  const assignRole = async (userId) => {
    const roleName = selectedRoles[userId];
    if (!roleName) {
      setMessage({ type: 'error', text: 'Please select a role to assign.' });
      return;
    }

    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/roles/tenants/${currentTenant}/domains/${domain_id}/users/${userId}/roles`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ role_name: roleName }),
        }
      );

      if (response.ok) {
        setMessage({ type: 'success', text: 'Role assigned successfully.' });
        fetchUsers();
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.detail || 'Failed to assign role.' });
      }
    } catch (error) {
      console.error('Error assigning role:', error);
      setMessage({ type: 'error', text: 'An error occurred while assigning the role.' });
    }
  };

  // Revoke role from a user
  const revokeRole = async (userId, roleName) => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/roles/tenants/${currentTenant}/domains/${domain_id}/users/${userId}/roles/${roleName}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setMessage({ type: 'success', text: 'Role revoked successfully.' });
        fetchUsers();
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.detail || 'Failed to revoke role.' });
      }
    } catch (error) {
      console.error('Error revoking role:', error);
      setMessage({ type: 'error', text: 'An error occurred while revoking the role.' });
    }
  };

  if (isLoading && Object.keys(config).length === 0) {
    return (
      <Box bg="gray.50" minH="100vh" py={12}>
        <Container maxW="container.xl">
          <Text>Loading configuration...</Text>
        </Container>
      </Box>
    );
  }

  return (
    <Box bg="gray.50" minH="100vh" py={12}>
      <Container maxW="container.xl">
        <Heading fontSize={{ base: '3xl', md: '4xl' }} fontWeight="bold" color="gray.800" mb={8}>
          Domain Configuration
        </Heading>

        {message && (
          <Alert status={message.type} mb={6}>
            <AlertIcon />
            {message.text}
          </Alert>
        )}

        <LLMConfigSection
          config={config}
          onConfigChange={handleInputChange}
          isLoading={isLoading}
        />
        <Divider my={8} />
        <ProcessingConfigSection
          config={config}
          onConfigChange={handleInputChange}
          isLoading={isLoading}
        />

        <Flex justify="center" mt={10}>
          <Button
            colorScheme="blue"
            size="lg"
            px={10}
            py={6}
            onClick={handleSubmit}
            isLoading={isLoading}
            shadow="md"
            _hover={{ bg: 'blue.600' }}
          >
            Save All Configuration Changes
          </Button>
        </Flex>

        {/* Role Management Section */}
        {["admin", "owner"].includes(currentUserRole) && (
          <>
            <Heading
              fontSize={{ base: '2xl', md: '3xl' }}
              fontWeight="bold"
              color="gray.800"
              mt={12}
              mb={8}
            >
              Manage User Roles
            </Heading>

            {users.length > 0 ? (
              <Stack spacing={6}>
                {users.map((user) => (
                  <Box
                    key={user.user_id}
                    p={6}
                    border="1px solid"
                    borderColor="gray.200"
                    borderRadius="lg"
                    bg="white"
                    shadow="sm"
                    _hover={{ shadow: 'md' }}
                  >
                    <Text fontSize="lg" mb={2} fontWeight="semibold" color="blue.600">
                      {user.name} ({user.email})
                    </Text>
                    <Text fontSize="md" color="gray.600" mb={4}>
                      Current Role: {user.role_name || 'No role assigned'}
                    </Text>
                    <Select
                      placeholder="Assign a new role"
                      value={selectedRoles[user.user_id] || ''}
                      onChange={(e) => handleRoleChange(user.user_id, e.target.value)}
                      mb={4}
                    >
                      {roles.map((role) => (
                        <option key={role.role_id} value={role.role_name}>
                          {role.role_name}
                        </option>
                      ))}
                    </Select>
                    <Flex>
                      <Button
                        colorScheme="blue"
                        onClick={() => assignRole(user.user_id)}
                        mr={4}
                        isDisabled={!selectedRoles[user.user_id]}
                      >
                        Assign Role
                      </Button>
                      {user.role_name && (
                        <Button
                          colorScheme="red"
                          onClick={() => revokeRole(user.user_id, user.role_name)}
                        >
                          Revoke Role
                        </Button>
                      )}
                    </Flex>
                  </Box>
                ))}
              </Stack>
            ) : (
              <Text fontSize="lg" color="gray.600" textAlign="center">
                No users found for this domain.
              </Text>
            )}
          </>
        )}
      </Container>
    </Box>
  );
};

export default DomainConfigPage;