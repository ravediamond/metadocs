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
import { useNavigate } from 'react-router-dom';

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

const HomePage = () => {
  const navigate = useNavigate();  // Navigation hook

  return (
    <Box bg="gray.100" minH="100vh" py={10}>
      {/* Hero Section */}
      <Box bg="white" shadow="md" py={{ base: 12, md: 16 }} mb={8}>
        <Container maxW="container.lg">
          <Stack spacing={6} textAlign="center">
            <Heading fontSize={{ base: '2xl', md: '4xl' }}>
              Enhance Your RAG Systems with Advanced Concept Management
            </Heading>
            <Text fontSize={{ base: 'lg', md: 'xl' }} color="gray.600">
              Manage domain-specific concepts and definitions, integrate with LangChain, 
              and dynamically detect undefined concepts—all in one place.
            </Text>
            <Stack direction={{ base: 'column', md: 'row' }} spacing={4} justify="center">
              <Button colorScheme="blue" size="md" onClick={() => navigate('/signup')}>
                Create an Account
              </Button>
              <Button variant="outline" colorScheme="blue" size="md" onClick={() => navigate('/login')}>
                Login
              </Button>
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxW="container.lg">
        <Stack spacing={8} textAlign="center">
          <Heading as="h2" size="lg" mb={4}>
            Key Features
          </Heading>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={8}>
            {features.map((feature, index) => (
              <Box
                key={index}
                p={6}
                border="1px"
                borderColor="gray.200"
                borderRadius="md"
                bg="white"
                shadow="sm"
                textAlign="left"
              >
                <Icon as={CheckCircleIcon} w={6} h={6} color="blue.500" mb={4} />
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

      {/* Call to Action Section */}
      <Box bg="white" mt={10} py={12} shadow="md">
        <Container maxW="container.lg">
          <VStack spacing={4}>
            <Heading as="h2" size="lg" mb={4}>
              Ready to Take Your RAG Systems to the Next Level?
            </Heading>
            <Text fontSize="md" color="gray.600" textAlign="center">
              Sign up now to start managing concepts, integrating with LangChain, and more!
            </Text>
            <Button colorScheme="blue" size="md" onClick={() => navigate('/signup')}>
              Get Started for Free
            </Button>
          </VStack>
        </Container>
      </Box>
    </Box>
  );
};

export default HomePage;