import React, { useState, useContext } from 'react';
import { Box, Input, Button, VStack, Heading, Text, FormControl, FormLabel } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const SignUpPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const { handleLogin } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, name }),
      });

      const data = await response.json();
      if (response.ok) {
        await handleLogin(email, password); // Automatically log in after successful registration
      } else {
        alert(data.detail || 'Registration failed');
      }
    } catch (error) {
      console.error('Sign up error:', error);
      alert('Error during sign up');
    }
  };

  return (
    <Box bg="gray.50" minH="100vh" display="flex" justifyContent="center" alignItems="center" p={6}>
      <Box
        bg="white"
        p={8}
        maxW="lg"
        w="full"
        borderRadius="lg"
        shadow="lg"
      >
        <VStack spacing={6}>
          <Heading as="h1" size="xl" textAlign="center" color="gray.800">
            Sign Up
          </Heading>
          <Text fontSize="lg" color="gray.600" textAlign="center">
            Create an account to get started.
          </Text>
          
          <form onSubmit={handleSubmit} style={{ width: '100%' }}>
            <VStack spacing={5}>
              {/* Name Input */}
              <FormControl id="name" isRequired>
                <FormLabel fontSize="lg" color="gray.700">Name</FormLabel>
                <Input
                  type="text"
                  placeholder="Enter your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  size="lg"
                  bg="gray.100"
                  _focus={{ bg: "white", borderColor: "blue.500" }}
                />
              </FormControl>

              {/* Email Input */}
              <FormControl id="email" isRequired>
                <FormLabel fontSize="lg" color="gray.700">Email</FormLabel>
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  size="lg"
                  bg="gray.100"
                  _focus={{ bg: "white", borderColor: "blue.500" }}
                />
              </FormControl>

              {/* Password Input */}
              <FormControl id="password" isRequired>
                <FormLabel fontSize="lg" color="gray.700">Password</FormLabel>
                <Input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  size="lg"
                  bg="gray.100"
                  _focus={{ bg: "white", borderColor: "blue.500" }}
                />
              </FormControl>

              {/* Submit Button */}
              <Button
                type="submit"
                colorScheme="blue"
                size="lg"
                width="full"
                py={6}
                _hover={{ bg: 'blue.600' }}
              >
                Sign Up
              </Button>
            </VStack>
          </form>
        </VStack>
      </Box>
    </Box>
  );
};

export default SignUpPage;