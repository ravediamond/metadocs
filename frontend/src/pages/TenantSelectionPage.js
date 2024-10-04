import React, { useContext } from 'react';
import { Box, Button, Stack, Heading, Text } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const TenantSelectionPage = () => {
  const { tenantIds, setCurrentTenant } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleTenantSelect = (tenantId) => {
    setCurrentTenant(tenantId);
    navigate('/dashboard');
  };

  return (
    <Box minH="100vh" display="flex" justifyContent="center" alignItems="center" p={4}>
      <Box
        bg="white"
        p={8}
        maxW="md"
        borderRadius="lg"
        shadow="lg"
        w="full"
        textAlign="center"
      >
        <Heading as="h2" size="xl" mb={6} color="gray.800">
          Select Tenant
        </Heading>
        <Text mb={4}>Please select a tenant to continue:</Text>
        <Stack spacing={4}>
          {tenantIds.map((tenantId) => (
            <Button
              key={tenantId}
              colorScheme="blue"
              size="lg"
              onClick={() => handleTenantSelect(tenantId)}
            >
              Tenant {tenantId}
            </Button>
          ))}
        </Stack>
      </Box>
    </Box>
  );
};

export default TenantSelectionPage;