import React, { useContext } from 'react';
import { Box, Button } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';
import { Link } from 'react-router-dom';

const Navbar = () => {
  const { token, handleLogout } = useContext(AuthContext);

  return (
    <Box p={4} bg="teal.500" color="white" display="flex" justifyContent="space-between">
      <Box>My App</Box>
      <Box>
        {token ? (
          <>
            <Button onClick={handleLogout} colorScheme="teal" mr={4}>
              Logout
            </Button>
            <Link to="/dashboard">Dashboard</Link>
          </>
        ) : (
          <>
            <Link to="/login" style={{ marginRight: '10px' }}>Login</Link>
            <Link to="/signup">Sign Up</Link>
          </>
        )}
      </Box>
    </Box>
  );
};

export default Navbar;