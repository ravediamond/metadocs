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
    <Box bg="gray.50" minH="100vh" py={10}>
      {/* Hero Section */}
      <Box bgGradient="linear(to-r, white, gray.50)" py={{ base: 12, md: 16 }} mb={8} shadow="sm">
        <Container maxW="container.xl">
          <Stack spacing={6} textAlign="center">
            <Heading fontSize={{ base: '3xl', md: '5xl' }} fontWeight="bold" color="gray.800">
              Elevate Your RAG System with Seamless Concept Management
            </Heading>
            <Text fontSize={{ base: 'lg', md: 'xl' }} color="gray.600" maxW="xl" mx="auto">
              Effortlessly manage domain-specific concepts, integrate with LangChain, and detect undefined terms dynamically.
            </Text>
            <Stack direction={{ base: 'column', md: 'row' }} spacing={4} justify="center" pt={4}>
              <Button
                colorScheme="blue"
                size="lg"
                px={8}
                py={6}
                onClick={() => navigate('/signup')}
                shadow="md"
                _hover={{ bg: "blue.600" }}
              >
                Get Started
              </Button>
              <Button
                variant="outline"
                colorScheme="blue"
                size="lg"
                px={8}
                py={6}
                onClick={() => navigate('/login')}
                _hover={{ bg: "gray.100" }}
              >
                Login
              </Button>
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxW="container.xl">
        <Stack spacing={8} textAlign="center">
          <Heading as="h2" size="xl" fontWeight="semibold" color="gray.800" mb={6}>
            Key Features
          </Heading>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={10}>
            {features.map((feature, index) => (
              <Box
                key={index}
                p={8}
                border="1px solid"
                borderColor="gray.200"
                borderRadius="lg"
                bg="white"
                shadow="sm"
                textAlign="left"
                transition="all 0.3s"
                _hover={{ shadow: "lg", transform: "scale(1.02)" }}
              >
                <Icon as={CheckCircleIcon} w={8} h={8} color="blue.500" mb={4} />
                <Heading as="h3" size="md" mb={2} color="gray.700">
                  {feature.title}
                </Heading>
                <Text fontSize="md" color="gray.600">
                  {feature.description}
                </Text>
              </Box>
            ))}
          </SimpleGrid>
        </Stack>
      </Container>

      {/* Call to Action Section */}
      <Box bgGradient="linear(to-r, gray.50, white)" mt={10} py={12} shadow="sm">
        <Container maxW="container.xl">
          <VStack spacing={6}>
            <Heading as="h2" size="xl" fontWeight="bold" color="gray.800" mb={4}>
              Ready to Transform Your Workflow?
            </Heading>
            <Text fontSize="lg" color="gray.600" maxW="md" textAlign="center">
              Join today to experience the power of dynamic concept management and seamless integration.
            </Text>
            <Button
              colorScheme="blue"
              size="lg"
              px={8}
              py={6}
              onClick={() => navigate('/signup')}
              shadow="md"
              _hover={{ bg: "blue.600" }}
            >
              Sign Up for Free
            </Button>
          </VStack>
        </Container>
      </Box>
    </Box>
  );
};

export default HomePage;