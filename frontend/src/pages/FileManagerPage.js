import React, { useState, useEffect, useContext } from 'react';
import {
  Box,
  Heading,
  Container,
  Text,
  Flex,
  Button,
  Input,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  IconButton,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { DeleteIcon } from '@chakra-ui/icons';
import AuthContext from '../context/AuthContext';

const FileManagerPage = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const navigate = useNavigate();
  const toast = useToast();

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [error, setError] = useState(null);

  // For delete confirmation modal
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [fileToDelete, setFileToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Fetch files on component mount and when domain_id changes
  useEffect(() => {
    const fetchFiles = async () => {
      setLoadingFiles(true);
      setError(null);
      try {
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/`,
          {
            method: 'GET',
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          setFiles(data);
        } else {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch files.');
        }
      } catch (err) {
        console.error('Error fetching files:', err);
        setError(err.message);
      } finally {
        setLoadingFiles(false);
      }
    };

    fetchFiles();
  }, [currentTenant, domain_id, token]);

  // Handle file selection
  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  // Handle file upload
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
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/upload`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      if (response.ok) {
        const uploadedFile = await response.json();
        toast({
          title: 'File uploaded successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setSelectedFile(null);
        // Refresh the file list
        setFiles((prevFiles) => [...prevFiles, uploadedFile]);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'File upload failed.');
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

  // Handle delete button click
  const handleDeleteClick = (file) => {
    setFileToDelete(file);
    onOpen();
  };

  // Confirm deletion
  const confirmDelete = async () => {
    if (!fileToDelete) return;

    setDeleting(true);
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/${fileToDelete.file_id}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.status === 204) {
        toast({
          title: 'File deleted successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        // Remove the deleted file from the list
        setFiles((prevFiles) =>
          prevFiles.filter((file) => file.file_id !== fileToDelete.file_id)
        );
        onClose();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete file.');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      toast({
        title: 'Deletion failed.',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Box bg="gray.50" minH="100vh" py={10}>
      <Container maxW="container.lg">
        <Heading
          fontSize="3xl"
          mb={8}
          fontWeight="bold"
          color="gray.900"
          textAlign="center"
        >
          File Manager for Domain
        </Heading>
        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8} mb={8}>
          <Text fontSize="lg" color="gray.700" mb={4}>
            Domain ID: <strong>{domain_id}</strong>
          </Text>
          <Flex direction="column" align="start">
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
            <Flex>
              <Button
                colorScheme="teal"
                size="lg"
                onClick={handleUpload}
                isLoading={uploading}
                loadingText="Uploading"
                mr={4}
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
          </Flex>
        </Box>

        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8}>
          <Heading fontSize="2xl" mb={4} color="gray.900">
            Uploaded Files
          </Heading>

          {loadingFiles ? (
            <Flex justify="center" align="center" py={10}>
              <Spinner size="xl" color="teal.500" />
            </Flex>
          ) : error ? (
            <Alert status="error" mb={4}>
              <AlertIcon />
              <AlertTitle mr={2}>Error:</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : files.length === 0 ? (
            <Text color="gray.600">No files uploaded yet.</Text>
          ) : (
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>Filename</Th>
                  <Th>Uploaded At</Th>
                  <Th>Uploaded By</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {files.map((file) => (
                  <Tr key={file.file_id}>
                    <Td>{file.filename}</Td>
                    <Td>{new Date(file.uploaded_at).toLocaleString()}</Td>
                    <Td>
                      {file.uploaded_by
                        ? file.uploaded_by
                        : 'Unknown'}
                    </Td>
                    <Td>
                      {/* You can add a download link if needed */}
                      {/* <Button size="sm" colorScheme="blue" mr={2}>
                        Download
                      </Button> */}
                      <IconButton
                        aria-label="Delete File"
                        icon={<DeleteIcon />}
                        colorScheme="red"
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteClick(file)}
                      />
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Box>
      </Container>

      {/* Delete Confirmation Modal */}
      <Modal isOpen={isOpen} onClose={onClose} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Delete File</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {fileToDelete && (
              <Text>
                Are you sure you want to delete{' '}
                <strong>{fileToDelete.filename}</strong>?
              </Text>
            )}
          </ModalBody>

          <ModalFooter>
            <Button
              colorScheme="red"
              mr={3}
              onClick={confirmDelete}
              isLoading={deleting}
            >
              Delete
            </Button>
            <Button variant="ghost" onClick={onClose} disabled={deleting}>
              Cancel
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default FileManagerPage;