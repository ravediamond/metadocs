import React, { useContext, useEffect, useState } from 'react';
import { Box, Heading, Text } from '@chakra-ui/react';
import AuthContext from '../context/AuthContext';

const DashboardPage = () => {
  const { user, token } = useContext(AuthContext);
  const [domains, setDomains] = useState([]);

  useEffect(() => {
    const fetchDomains = async () => {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/domains`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setDomains(data);
      } else {
        console.error('Failed to fetch domains');
      }
    };

    if (token) {
      fetchDomains();
    }
  }, [token]);

  return (
    <Box p={4}>
      <Heading>Welcome to the Dashboard, {user?.name}</Heading>
      <Text mt={4}>Here are your domains:</Text>
      {domains.length > 0 ? (
        <ul>
          {domains.map((domain) => (
            <li key={domain.domain_id}>{domain.domain_name}</li>
          ))}
        </ul>
      ) : (
        <Text>No domains found.</Text>
      )}
    </Box>
  );
};

export default DashboardPage;