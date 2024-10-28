import React, { useState, useContext } from 'react';
import {
  Box, Heading, Container, Text, Flex, Button, Input, useToast
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';

const FileUploadPage = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const navigate = useNavigate();
  const toast = useToast();

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast({
        title: 'No file selected.',
        description: 'Please choose a file to upload.',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setUploading(true);

    const formData = new FormData();
    formData.append('uploaded_file', selectedFile);

    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        toast({
          title: 'File uploaded successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setSelectedFile(null);
        navigate(`/domains/${domain_id}`); // Navigate back to DomainPage or another appropriate page
      } else {
        const errorData = await response.json();
        throw new Error(errorData.message || 'File upload failed.');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      toast({
        title: 'Upload failed.',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box bg="gray.50" minH="100vh" py={10}>
      <Container maxW="container.md">
        <Heading fontSize="3xl" mb={8} fontWeight="bold" color="gray.900" textAlign="center">
          Upload Files to Domain
        </Heading>
        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8}>
          <Text fontSize="lg" color="gray.700" mb={4}>
            Domain ID: <strong>{domain_id}</strong>
          </Text>
          <Input
            type="file"
            onChange={handleFileChange}
            mb={4}
            size="lg"
          />
          {selectedFile && (
            <Text mb={4} color="gray.600">
              Selected File: <strong>{selectedFile.name}</strong>
            </Text>
          )}
          <Flex justify="space-between">
            <Button
              colorScheme="teal"
              size="lg"
              onClick={handleUpload}
              isLoading={uploading}
              loadingText="Uploading"
            >
              Upload
            </Button>
            <Button
              variant="outline"
              colorScheme="red"
              size="lg"
              onClick={() => navigate(-1)}
            >
              Cancel
            </Button>
          </Flex>
        </Box>
      </Container>
    </Box>
  );
};

export default FileUploadPage;