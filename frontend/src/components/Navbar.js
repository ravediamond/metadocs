import React from 'react';
import { Box} from '@chakra-ui/react';
import { useAuth0 } from '@auth0/auth0-react';
import LoginButton from './LoginButton';
import LogoutButton from './LogoutButton';

const Navbar = () => {
  const { isAuthenticated } = useAuth0();

  return (
    <Box p={4} bg="teal.500" color="white" display="flex" justifyContent="space-between">
      <Box>My App</Box>
      {isAuthenticated ? (
        <LogoutButton/>
      ) : (
        <LoginButton/>
      )}
    </Box>
  );
};

export default Navbar;