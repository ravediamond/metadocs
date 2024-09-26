import React, { useContext } from 'react';
import { Box, Button } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';
import { Link } from 'react-router-dom';

const Navbar = () => {
  const { token, handleLogout } = useContext(AuthContext);

  return (
    <Box p={4} bg="#2979FF" color="white" display="flex" justifyContent="space-between">
      {/* Link to the homepage */}
      <Box fontWeight="bold">
        <Link to="/dashboard" style={{ textDecoration: 'none', color: 'white' }}>Metadocs</Link>
      </Box>
      <Box>
        {token ? (
          <>
            {/* Logout Button */}
            <Button onClick={handleLogout} bg="white" color="#2979FF" mr={4} _hover={{ bg: "#F1F1F1" }}>
              Logout
            </Button>
            {/* Dashboard Link as Button */}
            <Button as={Link} to="/dashboard" bg="white" color="#2979FF" _hover={{ bg: "#F1F1F1" }}>
              Dashboard
            </Button>
          </>
        ) : (
          <>
            {/* Login Link as Button */}
            <Button as={Link} to="/login" bg="white" color="#2979FF" mr={4} _hover={{ bg: "#F1F1F1" }}>
              Login
            </Button>
            {/* Sign Up Link as Button */}
            <Button as={Link} to="/signup" bg="white" color="#2979FF" _hover={{ bg: "#F1F1F1" }}>
              Sign Up
            </Button>
          </>
        )}
      </Box>
    </Box>
  );
};

export default Navbar;