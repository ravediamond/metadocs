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
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from '@chakra-ui/react';
import { useParams, useNavigate } from 'react-router-dom';
import { DeleteIcon, DownloadIcon, AddIcon } from '@chakra-ui/icons';
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

  // For version upload modal
  const {
    isOpen: isVersionOpen,
    onOpen: onVersionOpen,
    onClose: onVersionClose,
  } = useDisclosure();
  const [selectedFileForVersion, setSelectedFileForVersion] = useState(null);
  const [newVersionFile, setNewVersionFile] = useState(null);

  useEffect(() => {
    const fetchFiles = async () => {
      setLoadingFiles(true);
      setError(null);
      try {
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/files`,
          {
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

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleNewVersionChange = (e) => {
    setNewVersionFile(e.target.files[0]);
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

  const handleAddVersion = async () => {
    if (!newVersionFile || !selectedFileForVersion) return;

    const formData = new FormData();
    formData.append('uploaded_file', newVersionFile);

    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/files/${selectedFileForVersion.file_id}/versions`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      if (response.ok) {
        const newVersion = await response.json();
        toast({
          title: 'New version uploaded successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        
        // Update files list with new version
        setFiles(prevFiles => 
          prevFiles.map(file => 
            file.file_id === selectedFileForVersion.file_id 
              ? { ...file, versions: [...file.versions, newVersion] }
              : file
          )
        );
        
        onVersionClose();
        setNewVersionFile(null);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload new version.');
      }
    } catch (error) {
      toast({
        title: 'Failed to add version',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleDeleteClick = (file) => {
    setFileToDelete(file);
    onOpen();
  };

  const confirmDelete = async () => {
    if (!fileToDelete) return;

    setDeleting(true);
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/files/tenants/${currentTenant}/domains/${domain_id}/files/${fileToDelete.file_id}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        toast({
          title: 'File deleted successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
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
      <Container maxW="container.xl">
        <Heading fontSize="3xl" mb={8} fontWeight="bold" color="gray.900" textAlign="center">
          File Manager
        </Heading>

        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8} mb={8}>
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
            <Accordion allowMultiple>
              {files.map((file) => (
                <AccordionItem key={file.file_id}>
                  <AccordionButton>
                    <Box flex="1">
                      <Flex justify="space-between" align="center">
                        <Text fontWeight="medium">{file.filename}</Text>
                        <Text color="gray.600" fontSize="sm">
                          {new Date(file.uploaded_at).toLocaleString()}
                        </Text>
                      </Flex>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel>
                    <Box>
                      <Flex justify="space-between" mb={4}>
                        <Button
                          leftIcon={<AddIcon />}
                          colorScheme="blue"
                          size="sm"
                          onClick={() => {
                            setSelectedFileForVersion(file);
                            onVersionOpen();
                          }}
                        >
                          Add Version
                        </Button>
                        <IconButton
                          aria-label="Delete File"
                          icon={<DeleteIcon />}
                          colorScheme="red"
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteClick(file)}
                        />
                      </Flex>
                      
                      <Table size="sm">
                        <Thead>
                          <Tr>
                            <Th>Version</Th>
                            <Th>Created At</Th>
                            <Th>Actions</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {file.versions.map((version) => (
                            <Tr key={version.file_version_id}>
                              <Td>v{version.version}</Td>
                              <Td>{new Date(version.created_at).toLocaleString()}</Td>
                              <Td>
                                <IconButton
                                  aria-label="Download Version"
                                  icon={<DownloadIcon />}
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {/* Implement version download */}}
                                />
                              </Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </Box>
                  </AccordionPanel>
                </AccordionItem>
              ))}
            </Accordion>
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
                Are you sure you want to delete all versions of <strong>{fileToDelete.filename}</strong>?
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

      {/* New Version Modal */}
      <Modal isOpen={isVersionOpen} onClose={onVersionClose} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Add New Version</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Input
              type="file"
              onChange={handleNewVersionChange}
              mb={4}
            />
          </ModalBody>
          <ModalFooter>
            <Button
              colorScheme="blue"
              mr={3}
              onClick={handleAddVersion}
              isDisabled={!newVersionFile}
            >
              Upload Version
            </Button>
            <Button variant="ghost" onClick={onVersionClose}>
              Cancel
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default FileManagerPage;