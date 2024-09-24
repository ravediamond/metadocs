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

const NewDomainPage = () => {
  const { token } = useContext(AuthContext);
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
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          DomainName: domainName,
          Description: description,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        toast({
          title: 'Domain created successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        navigate('/dashboard');
      } else {
        toast({
          title: data.message || 'Failed to create domain.',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: 'Error creating domain.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }

    setLoading(false);
  };

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      <Container maxW="container.md" bg="white" p={8} borderRadius="md" shadow="md">
        <Stack spacing={6}>
          <Heading as="h1" size="xl" textAlign="center">
            Create New Domain
          </Heading>
          <Text fontSize="md" color="gray.600" textAlign="center">
            Add a new domain to manage your data efficiently.
          </Text>

          <form onSubmit={handleSubmit}>
            <Stack spacing={4}>
              {/* Domain Name Input */}
              <FormControl id="domain-name" isRequired>
                <FormLabel>Domain Name</FormLabel>
                <Input
                  type="text"
                  placeholder="Enter domain name"
                  value={domainName}
                  onChange={(e) => setDomainName(e.target.value)}
                  bg="gray.50"
                  borderColor="gray.200"
                />
              </FormControl>

              {/* Description Textarea */}
              <FormControl id="description">
                <FormLabel>Description</FormLabel>
                <Textarea
                  placeholder="Enter domain description (optional)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  bg="gray.50"
                  borderColor="gray.200"
                />
              </FormControl>

              {/* Submit Button */}
              <Button
                colorScheme="blue"
                size="md"
                type="submit"
                isLoading={loading}
                loadingText="Creating Domain"
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