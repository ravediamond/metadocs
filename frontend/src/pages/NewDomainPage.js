import React, { useState, useContext } from 'react';
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Stack,
  Heading,
  Text,
  useToast,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import { domains } from '../api/api';

const NewDomainPage = () => {
  const { token, currentTenant } = useContext(AuthContext);
  const [domainName, setDomainName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!domainName) {
      toast({
        title: 'Domain Name is required.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setLoading(true);

    try {
      // Use domains.create from api.js with correct schema
      await domains.create(currentTenant, {
        domain_name: domainName,
        description: description,
        tenant_id: currentTenant
      }, token);

      toast({
        title: 'Domain created successfully.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      navigate('/dashboard');
    } catch (error) {
      toast({
        title: error.message || 'Failed to create domain.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }

    setLoading(false);
  };

  return (
    <Box bg="gray.50" minH="100vh" py={12} display="flex" justifyContent="center" alignItems="center">
      <Container maxW="container.md" bg="white" p={10} borderRadius="lg" shadow="lg">
        <Stack spacing={8}>
          <Heading as="h1" size="xl" textAlign="center" fontWeight="bold" color="gray.800">
            Create New Domain
          </Heading>
          <Text fontSize="lg" color="gray.600" textAlign="center">
            Add a new domain to manage your data efficiently.
          </Text>

          <form onSubmit={handleSubmit}>
            <Stack spacing={6}>
              {/* Domain Name Input */}
              <FormControl id="domain-name" isRequired>
                <FormLabel fontSize="lg" color="gray.700">Domain Name</FormLabel>
                <Input
                  type="text"
                  placeholder="Enter domain name"
                  value={domainName}
                  onChange={(e) => setDomainName(e.target.value)}
                  size="lg"
                  bg="gray.100"
                  _focus={{ bg: "white", borderColor: "blue.500" }}
                />
              </FormControl>

              {/* Description Textarea */}
              <FormControl id="description">
                <FormLabel fontSize="lg" color="gray.700">Description</FormLabel>
                <Textarea
                  placeholder="Enter domain description (optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  size="lg"
                  bg="gray.100"
                  _focus={{ bg: "white", borderColor: "blue.500" }}
                />
              </FormControl>

              {/* Submit Button */}
              <Button
                colorScheme="blue"
                size="lg"
                type="submit"
                isLoading={loading}
                loadingText="Creating Domain"
                py={6}
                _hover={{ bg: 'blue.600' }}
              >
                Create Domain
              </Button>
            </Stack>
          </form>
        </Stack>
      </Container>
    </Box>
  );
};

export default NewDomainPage;