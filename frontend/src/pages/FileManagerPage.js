import React, { useState, useEffect, useContext } from 'react';
import {
  Box,
  Container,
  Heading,
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
  IconButton,
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
  Spinner,
} from '@chakra-ui/react';
import { DeleteIcon, AddIcon, DownloadIcon } from '@chakra-ui/icons';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';

const FileUploadPage = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const navigate = useNavigate();
  const toast = useToast();

  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [error, setError] = useState(null);

  // Modals
  const { 
    isOpen: isDeleteOpen, 
    onOpen: onDeleteOpen, 
    onClose: onDeleteClose 
  } = useDisclosure();
  const {
    isOpen: isVersionOpen,
    onOpen: onVersionOpen,
    onClose: onVersionClose,
  } = useDisclosure();

  const [fileToDelete, setFileToDelete] = useState(null);
  const [selectedFileForVersion, setSelectedFileForVersion] = useState(null);
  const [newVersionFile, setNewVersionFile] = useState(null);

  // Fetch files on component mount
  useEffect(() => {
    fetchFiles();
  }, [currentTenant, domain_id, token]);

  const DateFormatter = ({ dateString }) => {
    const formatDate = (date) => {
      try {
        return new Date(Date.parse(date)).toLocaleString();
      } catch (error) {
        console.error('Date parsing error:', error);
        return 'Invalid date';
      }
    };
  
    return <>{formatDate(dateString)}</>;
  };

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
        console.log('Fetched files:', data);
        setFiles(data);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch files.');
      }
    } catch (err) {
      console.error('Error fetching files:', err);
      setError(err.message);
      toast({
        title: 'Error fetching files',
        description: err.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleNewVersionChange = (e) => {
    setNewVersionFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast({
        title: 'No file selected',
        description: 'Please select a file to upload',
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
          title: 'File uploaded successfully',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setSelectedFile(null);
        setFiles(prevFiles => [...prevFiles, uploadedFile]);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'File upload failed.');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      toast({
        title: 'Upload failed',
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
          title: 'New version uploaded successfully',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        
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

  const handleDelete = async () => {
    if (!fileToDelete) return;

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
          title: 'File deleted successfully',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setFiles(prevFiles => prevFiles.filter(file => file.file_id !== fileToDelete.file_id));
        onDeleteClose();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete file.');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      toast({
        title: 'Deletion failed',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  return (
    <Box minH="100vh" bg="gray.50" py={10}>
      <Container maxW="container.xl">
        <Heading mb={8} textAlign="center">File Manager</Heading>

        {/* Upload Section */}
        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8} mb={8}>
          <Flex direction="column" gap={4}>
            <Input
              type="file"
              onChange={handleFileChange}
              padding={1}
            />
            {selectedFile && (
              <Text color="gray.600">
                Selected: <strong>{selectedFile.name}</strong>
              </Text>
            )}
            <Flex gap={4}>
              <Button
                colorScheme="blue"
                onClick={handleUpload}
                isLoading={uploading}
                loadingText="Uploading"
              >
                Upload
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate(-1)}
              >
                Cancel
              </Button>
            </Flex>
          </Flex>
        </Box>

        {/* Files List */}
        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8}>
          <Heading size="md" mb={6}>Uploaded Files</Heading>
          
          {loadingFiles ? (
            <Flex justify="center" py={8}>
              <Spinner size="xl" />
            </Flex>
          ) : error ? (
            <Text color="red.500" textAlign="center" py={8}>{error}</Text>
          ) : files.length === 0 ? (
            <Text color="gray.500" textAlign="center" py={8}>
              No files uploaded yet
            </Text>
          ) : (
            <Accordion allowMultiple>
              {files.map((file) => (
                <AccordionItem key={file.filename}>
                  <AccordionButton>
                    <Flex flex="1" justify="space-between" align="center">
                      <Text fontWeight="medium">{file.filename}</Text>
                      <Text fontSize="sm" color="gray.500">
                        <DateFormatter dateString={file.created_at} />
                      </Text>
                    </Flex>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel pb={4}>
                    <Flex justify="space-between" mb={4}>
                      <Button
                        leftIcon={<AddIcon />}
                        size="sm"
                        onClick={() => {
                          setSelectedFileForVersion(file);
                          onVersionOpen();
                        }}
                      >
                        Add Version
                      </Button>
                      <IconButton
                        icon={<DeleteIcon />}
                        colorScheme="red"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setFileToDelete(file);
                          onDeleteOpen();
                        }}
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
                            <Td>v{version.version_number}</Td>
                            <Td><DateFormatter dateString={version.created_at} /></Td>
                            <Td>
                              <IconButton
                                icon={<DownloadIcon />}
                                size="sm"
                                variant="ghost"
                                onClick={() => {/* Implement download */}}
                              />
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </AccordionPanel>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </Box>

        {/* Delete Confirmation Modal */}
        <Modal isOpen={isDeleteOpen} onClose={onDeleteClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Delete File</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              Are you sure you want to delete{' '}
              <strong>{fileToDelete?.filename}</strong> and all its versions?
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="red" mr={3} onClick={handleDelete}>
                Delete
              </Button>
              <Button variant="ghost" onClick={onDeleteClose}>
                Cancel
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* New Version Modal */}
        <Modal isOpen={isVersionOpen} onClose={onVersionClose}>
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
                isLoading={uploading}
                loadingText="Uploading"
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
      </Container>
    </Box>
  );
};

export default FileUploadPage;