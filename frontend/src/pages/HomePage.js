import React from 'react';
import {
  Box,
  Button,
  Container,
  Heading,
  Text,
  Stack,
  SimpleGrid,
  Icon,
  VStack,
} from '@chakra-ui/react';
import { CheckCircleIcon } from '@chakra-ui/icons';

const features = [
  {
    title: 'Concept and Definition Management',
    description:
      'Centralized repository for managing domain-specific concepts, including categorization and synonym support.',
  },
  {
    title: 'LangChain Integration',
    description:
      'Dedicated API endpoints and pre-built components for seamless integration with LangChain-based RAG pipelines.',
  },
  {
    title: 'Service Account Management',
    description:
      'Create and manage service accounts with role-based access control and API key generation.',
  },
  {
    title: 'Semantic Search and Synonym Support',
    description:
      'Retrieve relevant concepts using embeddings and manage synonyms for better search accuracy.',
  },
  {
    title: 'User Roles and Permissions',
    description:
      'Role-based access control to manage user permissions and invite users with specific roles.',
  },
  {
    title: 'Analytics Dashboard',
    description:
      'View usage statistics, most searched concepts, and user engagement through a comprehensive dashboard.',
  },
  {
    title: 'Undefined Concept Detection',
    description:
      'Detect undefined terms through user query analysis and provide a feedback loop for suggestions.',
  },
];

const LandingPage = () => {
  return (
    <Box>
      {/* Hero Section */}
      <Box
        bgGradient="linear(to-r, teal.500, blue.500)"
        color="white"
        py={{ base: 20, md: 28 }}
      >
        <Container maxW="container.lg">
          <Stack spacing={6} textAlign="center">
            <Heading fontSize={{ base: '3xl', md: '5xl' }}>
              Enhance Your RAG Systems with Advanced Concept Management
            </Heading>
            <Text fontSize={{ base: 'md', md: 'xl' }}>
              Manage domain-specific concepts and definitions, integrate with
              LangChain, and dynamically detect undefined concepts—all in one
              place.
            </Text>
            <Stack
              direction={{ base: 'column', md: 'row' }}
              spacing={4}
              align="center"
              justify="center"
            >
              <Button colorScheme="teal" size="lg">
                Get Started
              </Button>
              <Button variant="outline" colorScheme="teal" size="lg">
                Learn More
              </Button>
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Features Section */}
      <Box py={{ base: 16, md: 24 }}>
        <Container maxW="container.lg">
          <Stack spacing={12} textAlign="center">
            <Heading as="h2" size="xl">
              Key Features
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={10}>
              {features.map((feature, index) => (
                <Box key={index} p={5} textAlign="left">
                  <Icon as={CheckCircleIcon} w={8} h={8} color="teal.500" mb={4} />
                  <Heading as="h3" size="md" mb={2}>
                    {feature.title}
                  </Heading>
                  <Text fontSize="sm" color="gray.600">
                    {feature.description}
                  </Text>
                </Box>
              ))}
            </SimpleGrid>
          </Stack>
        </Container>
      </Box>

      {/* Call to Action Section */}
      <Box bg="gray.50" py={{ base: 16, md: 24 }}>
        <Container maxW="container.lg">
          <VStack spacing={6}>
            <Heading as="h2" size="lg">
              Ready to Take Your RAG Systems to the Next Level?
            </Heading>
            <Text fontSize={{ base: 'md', md: 'lg' }} color="gray.600" textAlign="center">
              Sign up now to start managing concepts, integrating with LangChain, and more!
            </Text>
            <Button colorScheme="teal" size="lg">
              Get Started for Free
            </Button>
          </VStack>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;