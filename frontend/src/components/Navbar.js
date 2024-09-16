import React from 'react';
import { Box, Button } from '@chakra-ui/react';
import { useAuth0 } from '@auth0/auth0-react';

const Navbar = () => {
  const { loginWithRedirect, logout, isAuthenticated } = useAuth0();

  return (
    <Box p={4} bg="teal.500" color="white" display="flex" justifyContent="space-between">
      <Box>My App</Box>
      {isAuthenticated ? (
        <Button colorScheme="teal" variant="outline" onClick={() => logout({ returnTo: window.location.origin })}>
          Logout
        </Button>
      ) : (
        <Button colorScheme="teal" variant="solid" onClick={loginWithRedirect}>
          Login
        </Button>
      )}
    </Box>
  );
};

export default Navbar;