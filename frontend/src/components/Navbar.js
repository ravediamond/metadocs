import React, { useContext } from 'react';
import { Box, Button, Flex, Heading } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';
import { Link } from 'react-router-dom';

const Navbar = () => {
  const { token, handleLogout } = useContext(AuthContext);

  return (
    <Box bg="blue.500" color="white" py={4} px={6} shadow="md">
      <Flex justify="space-between" align="center" maxW="container.xl" mx="auto">
        {/* Brand / Logo */}
        <Heading as={Link} to="/dashboard" size="lg" color="white" fontWeight="bold" _hover={{ textDecoration: 'none' }}>
          Metadocs
        </Heading>

        {/* Navigation Links */}
        <Flex align="center">
          {token ? (
            <>
              {/* Logout Button */}
              <Button
                onClick={handleLogout}
                bg="white"
                color="blue.500"
                mr={4}
                _hover={{ bg: "gray.100" }}
              >
                Logout
              </Button>
            </>
          ) : (
            <>
              {/* Login Button */}
              <Button
                as={Link}
                to="/login"
                bg="white"
                color="blue.500"
                mr={4}
                _hover={{ bg: "gray.100" }}
              >
                Login
              </Button>
              {/* Sign Up Button */}
              <Button
                as={Link}
                to="/signup"
                bg="white"
                color="blue.500"
                _hover={{ bg: "gray.100" }}
              >
                Sign Up
              </Button>
            </>
          )}
        </Flex>
      </Flex>
    </Box>
  );
};

export default Navbar;