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
} from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const DomainConfigPage = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const [config, setConfig] = useState([]);
  const [newConfig, setNewConfig] = useState({});
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedRoles, setSelectedRoles] = useState({});
  const [message, setMessage] = useState(null);

  // Fetch domain configuration
  const fetchConfig = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/config`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
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

  // Fetch users in the domain
  const fetchUsers = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/users`,
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
        `${process.env.REACT_APP_BACKEND_URL}/tenants/${currentTenant}/roles`,
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain_id, token]);

  const handleInputChange = (key, value) => {
    setNewConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    for (const key in newConfig) {
      try {
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/config`,
          {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              config_key: key,
              config_value: newConfig[key],
            }),
          }
        );

        if (!response.ok) {
          console.error('Failed to update config');
        }
      } catch (error) {
        console.error('Error updating config:', error);
      }
    }
    window.location.reload();
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
        `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/users/${userId}/roles`,
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
        `${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains/${domain_id}/users/${userId}/roles/${roleName}`,
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

  return (
    <Box bg="gray.50" minH="100vh" py={12}>
      <Container maxW="container.xl">
        <Heading
          fontSize={{ base: '3xl', md: '4xl' }}
          fontWeight="bold"
          color="gray.800"
          mb={8}
        >
          Domain Configuration
        </Heading>

        {message && (
          <Alert status={message.type} mb={6}>
            <AlertIcon />
            {message.text}
          </Alert>
        )}

        {/* Domain Configurations */}
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

        {/* User Role Management */}
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
                >
                  {roles.map((role) => (
                    <option key={role.role_id} value={role.role_name}>
                      {role.role_name}
                    </option>
                  ))}
                </Select>
                <Flex mt={4}>
                  <Button
                    colorScheme="blue"
                    onClick={() => assignRole(user.user_id)}
                    mr={4}
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
      </Container>
    </Box>
  );
};

export default DomainConfigPage;