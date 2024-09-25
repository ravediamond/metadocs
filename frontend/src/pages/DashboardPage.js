import React, { useContext, useEffect, useState } from 'react';
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Container,
  Stack,
  Button,
  VStack,
  Flex,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import AuthContext from '../context/AuthContext';

const DashboardPage = () => {
  const { user, token } = useContext(AuthContext);
  const [domains, setDomains] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDomains = async () => {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setDomains(data);
      } else {
        console.error('Failed to fetch domains');
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
            <Stack spacing={3}>
              <Heading fontSize={{ base: '2xl', md: '4xl' }}>
                Welcome to the Dashboard, {user?.name}
              </Heading>
              <Text fontSize={{ base: 'lg', md: 'xl' }} color="gray.600">
                Manage your data efficiently and view detailed information for each domain.
              </Text>
            </Stack>
            {/* Move button to top-left */}
            <Button
              colorScheme="blue"
              size="md"
              onClick={() => navigate('/new-domain')}
            >
              Add New Domain
            </Button>
          </Flex>
        </Container>
      </Box>

      {/* Domains Section */}
      <Container maxW="container.lg">
        <Stack spacing={12} textAlign="center">
          <Heading as="h2" size="lg" mb={4}>
            Your Domains
          </Heading>

          {domains.length > 0 ? (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={8}>
              {domains.map((domain) => (
                <DomainCard key={domain.domain_id} domain={domain} />
              ))}
            </SimpleGrid>
          ) : (
            <Text>No domains found.</Text>
          )}
        </Stack>
      </Container>
    </Box>
  );
};

// DomainCard component for displaying each domain
const DomainCard = ({ domain }) => (
  <Box
    p={6}
    border="1px"
    borderColor="gray.200"
    borderRadius="md"
    bg="white"
    shadow="sm"
    textAlign="left"
  >
    <Heading as="h3" size="md" mb={2}>
      {domain.domain_name}
    </Heading>
    <Text fontSize="sm" color="gray.600" mb={4}>
      {domain.description || 'No description available'}
    </Text>
    <Text fontSize="xs" color="gray.500">
      Created at: {new Date(domain.created_at).toLocaleDateString()}
    </Text>
  </Box>
);

// PropTypes for DomainCard
DomainCard.propTypes = {
  domain: PropTypes.shape({
    domain_id: PropTypes.string.isRequired,
    domain_name: PropTypes.string.isRequired,
    description: PropTypes.string,
    created_at: PropTypes.string.isRequired,
  }).isRequired,
};

export default DashboardPage;