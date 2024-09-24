import React, { useState, useContext } from 'react';
import { Box, Input, Button } from '@chakra-ui/react';
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
    <Box p={4}>
      <form onSubmit={handleSubmit}>
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
        <Button type="submit" colorScheme="teal">
          Login
        </Button>
      </form>
    </Box>
  );
};

export default LoginPage;