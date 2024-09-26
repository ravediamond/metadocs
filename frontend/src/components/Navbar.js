import React, { useContext } from 'react';
import { Box, Button } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';
import { Link } from 'react-router-dom';

const Navbar = () => {
  const { token, handleLogout } = useContext(AuthContext);

  return (
    <Box p={4} bg="teal.500" color="white" display="flex" justifyContent="space-between">
      {/* Link to the homepage */}
      <Box fontWeight="bold">
        <Link to="/dashboard" style={{ textDecoration: 'none', color: 'white' }}>Metadocs</Link>
      </Box>
      <Box>
        {token ? (
          <>
            {/* Logout Button */}
            <Button onClick={handleLogout} colorScheme="teal" mr={4}>
              Logout
            </Button>
            {/* Dashboard Link as Button */}
            <Button as={Link} to="/dashboard" colorScheme="teal">
              Dashboard
            </Button>
          </>
        ) : (
          <>
            {/* Login Link as Button */}
            <Button as={Link} to="/login" colorScheme="teal" mr={4}>
              Login
            </Button>
            {/* Sign Up Link as Button */}
            <Button as={Link} to="/signup" colorScheme="teal">
              Sign Up
            </Button>
          </>
        )}
      </Box>
    </Box>
  );
};

export default Navbar;