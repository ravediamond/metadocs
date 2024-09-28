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
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import AuthContext from '../context/AuthContext';

const DashboardPage = () => {
  const { user, token } = useContext(AuthContext);
  const [domains, setDomains] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchDomains = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains`, {
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
  }, [token]);

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      {/* Header Section */}
      <Box bg="white" shadow="md" py={8} mb={8}>
        <Container maxW="container.lg">
          <Flex justify="space-between" alignItems="center">
            <Stack spacing={3} alignItems="flex-start">
              <Heading fontSize={{ base: '2xl', md: '4xl' }} color="blue.800">
                Welcome{user?.name ? `, ${user.name}` : ''}
              </Heading>
              <Text fontSize={{ base: 'lg', md: 'xl' }} color="gray.600">
                Manage your data efficiently and explore your domains.
              </Text>
            </Stack>
            {/* Action Buttons */}
            <HStack spacing={4}>
              <Button colorScheme="blue" size="md" onClick={() => navigate('/new-domain')}>
                Add New Domain
              </Button>
              <Button colorScheme="green" size="md" onClick={() => navigate('/user/config')}>
                User Settings
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Domains Section */}
      <Container maxW="container.lg">
        <Stack spacing={12} textAlign="center">
          <Heading as="h2" size="lg" color="blue.700" mb={4}>
            Your Domains
          </Heading>

          {isLoading ? (
            <Spinner size="xl" />
          ) : error ? (
            <Text color="red.500">{error}</Text>
          ) : domains.length > 0 ? (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={8}>
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
const DomainCard = ({ domain, onClick }) => (
  <Box
    p={6}
    border="1px"
    borderColor="gray.200"
    borderRadius="md"
    bg="white"
    shadow="sm"
    transition="all 0.2s"
    _hover={{ transform: 'scale(1.02)', boxShadow: 'lg' }}
    textAlign="left"
    onClick={onClick}
    cursor="pointer"
  >
    <Heading as="h3" size="md" mb={2} color="blue.600">
      {domain.domain_name}
    </Heading>
    <Text fontSize="sm" color="gray.600" mb={4}>
      {domain.description || 'No description available'}
    </Text>
    <Text fontSize="xs" color="gray.500">
      Created at:{' '}
      {domain.created_at ? new Date(domain.created_at).toLocaleDateString() : 'N/A'}
    </Text>
  </Box>
);

// PropTypes for DomainCard
DomainCard.propTypes = {
  domain: PropTypes.shape({
    domain_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    domain_name: PropTypes.string.isRequired,
    description: PropTypes.string,
    created_at: PropTypes.string,
  }).isRequired,
  onClick: PropTypes.func.isRequired,
};

export default DashboardPage;