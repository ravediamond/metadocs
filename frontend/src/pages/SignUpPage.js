import React, { useState, useContext } from 'react';
import { Box, Input, Button, VStack, Heading } from '@chakra-ui/react';
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
        await handleLogin(email, password);  // Automatically log in after successful registration
      } else {
        alert(data.detail || 'Registration failed');
      }
    } catch (error) {
      console.error('Sign up error:', error);
      alert('Error during sign up');
    }
  };

  return (
    <Box p={4} maxW="md" mx="auto">
      <VStack spacing={4}>
        <Heading>Sign Up</Heading>
        <form onSubmit={handleSubmit}>
          <Input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            mb={3}
          />
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            mb={3}
          />
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            mb={3}
          />
          <Button type="submit" colorScheme="teal" width="full">
            Sign Up
          </Button>
        </form>
      </VStack>
    </Box>
  );
};

export default SignUpPage;