import React, { useState, useContext } from 'react';
import { Box, Input, Button, Heading, Text, Stack, FormControl } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { handleLogin } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    await handleLogin(email, password);
  };

  return (
    <Box bg="gray.50" minH="100vh" display="flex" justifyContent="center" alignItems="center" p={4}>
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
          Login
        </Heading>

        <form onSubmit={handleSubmit}>
          <Stack spacing={6}>
            <FormControl>
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                size="lg"
                bg="gray.100"
                _focus={{ bg: "white", borderColor: "blue.500" }}
              />
            </FormControl>

            <FormControl>
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                size="lg"
                bg="gray.100"
                _focus={{ bg: "white", borderColor: "blue.500" }}
              />
            </FormControl>

            <Button
              type="submit"
              colorScheme="blue"
              size="lg"
              w="full"
              py={6}
              _hover={{ bg: 'blue.600' }}
            >
              Login
            </Button>
          </Stack>
        </form>

        <Text mt={4} color="gray.600">
          Don't have an account? <Button variant="link" colorScheme="blue">Sign Up</Button>
        </Text>
      </Box>
    </Box>
  );
};

export default LoginPage;