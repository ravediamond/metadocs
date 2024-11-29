import React, { useContext, useEffect, useState } from 'react';
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Container,
  Stack,
  Button,
  Flex,
  Spinner,
  HStack,
  VStack,
  Divider,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import {
  FaFile,
  FaCog,
  FaProjectDiagram,
  FaNetworkWired,
  FaHistory,
  FaUserCog,
  FaPlus,
} from 'react-icons/fa';
import AuthContext from '../context/AuthContext';


const DashboardPage = () => {
  const { user, token, currentTenant } = useContext(AuthContext);
  const [domains, setDomains] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    if (!currentTenant) {
      // If no tenant is selected, redirect to tenant selection page
      navigate('/select-tenant');
      return;
    }
    const fetchDomains = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains/tenants/${currentTenant}/domains`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch domains');
        }
        const data = await response.json();
        setDomains(data);
      } catch (error) {
        console.error('Error fetching domains:', error);
        setError(error.message);
      } finally {
        setIsLoading(false);
      }
    };

    if (token) {
      fetchDomains();
    }
  }, [token, currentTenant, navigate]);

  return (
    <Box bg="gray.50" minH="100vh" py={10}>
      {/* Header Section */}
      <Box bg="white" shadow="sm" py={8} mb={8}>
        <Container maxW="container.xl">
          <Flex justify="space-between" alignItems="center">
            <Stack spacing={3} alignItems="flex-start">
              <Heading fontSize={{ base: '3xl', md: '5xl' }} fontWeight="bold" color="gray.800">
                Welcome{user?.name ? `, ${user.name}` : ''}
              </Heading>
              <Text fontSize={{ base: 'lg', md: 'xl' }} color="gray.600">
                Manage your data efficiently and explore your domains.
              </Text>
            </Stack>
            {/* Action Buttons */}
            <HStack spacing={4}>
              <Button
                colorScheme="blue"
                size="lg"
                onClick={() => navigate('/new-domain')}
                shadow="md"
                _hover={{ bg: "blue.600" }}
              >
                Add New Domain
              </Button>
              <Button
                colorScheme="green"
                size="lg"
                onClick={() => navigate('/user/config')}
                shadow="md"
                _hover={{ bg: "green.600" }}
              >
                User Settings
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Domains Section */}
      <Container maxW="container.xl">
        <Stack spacing={12} textAlign="center">
          <Heading as="h2" size="xl" fontWeight="semibold" color="gray.700" mb={6}>
            Your Domains
          </Heading>

          {isLoading ? (
            <Spinner size="xl" />
          ) : error ? (
            <Text color="red.500">{error}</Text>
          ) : domains.length > 0 ? (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={10}>
              {domains.map((domain) => (
                <DomainCard
                  key={domain.domain_id}
                  domain={domain}
                  onClick={() => navigate(`/domain/${domain.domain_id}`)}
                />
              ))}
            </SimpleGrid>
          ) : (
            <Text color="gray.600">No domains found. Please add a new domain.</Text>
          )}
        </Stack>
      </Container>
    </Box>
  );
};

// DomainCard component for displaying each domain
const DomainCard = ({ domain }) => {
  const navigate = useNavigate(); // Add useNavigate hook

  return (
    <Box
      p={8}
      border="1px solid"
      borderColor="gray.200"
      borderRadius="lg"
      bg="white"
      shadow="sm"
      transition="all 0.3s"
      _hover={{ shadow: "lg" }}
      textAlign="left"
    >
      <VStack align="stretch" spacing={4}>
        <Box onClick={() => navigate(`/domain/${domain.domain_id}`)} cursor="pointer">
          <Heading as="h3" size="md" mb={2} color="blue.600">
            {domain.domain_name}
          </Heading>
          <Text fontSize="md" color="gray.600" mb={4}>
            {domain.description || 'No description available'}
          </Text>
          <Text fontSize="xs" color="gray.500">
            Created at: {domain.created_at ? new Date(domain.created_at).toLocaleDateString() : 'N/A'}
          </Text>
        </Box>

        <Divider />

        <SimpleGrid columns={2} spacing={3}>
          <Button
            size="sm"
            leftIcon={<FaFile />}
            variant="outline"
            onClick={() => navigate(`/domains/${domain.domain_id}/files`)}
          >
            Files
          </Button>

          <Button
            size="sm"
            leftIcon={<FaCog />}
            variant="outline"
            onClick={() => navigate(`/domains/${domain.domain_id}/config`)}
          >
            Settings
          </Button>

          <Button
            size="sm"
            leftIcon={<FaProjectDiagram />}
            colorScheme="blue"
            variant="outline"
            onClick={() => navigate(`/domains/${domain.domain_id}/process`)}
          >
            Process
          </Button>

          <Button
            size="sm"
            leftIcon={<FaNetworkWired />}
            colorScheme="green"
            variant="outline"
            onClick={() => navigate(`/domains/${domain.domain_id}/graph`)}
          >
            Graph
          </Button>

          <Button
            size="sm"
            leftIcon={<FaHistory />}
            colorScheme="purple"
            variant="outline"
            onClick={() => navigate(`/domains/${domain.domain_id}/versions`)}
            gridColumn="span 2"
          >
            Versions
          </Button>
        </SimpleGrid>
      </VStack>
    </Box>
  );
};

// Update PropTypes
DomainCard.propTypes = {
  domain: PropTypes.shape({
    domain_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    domain_name: PropTypes.string.isRequired,
    description: PropTypes.string,
    created_at: PropTypes.string,
  }).isRequired,
};

export default DashboardPage;