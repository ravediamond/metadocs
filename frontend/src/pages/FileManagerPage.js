import React, { useState, useEffect, useContext } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  Flex,
  Button,
  Input,
  Textarea,
  useToast,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  IconButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Spinner,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';
import { DeleteIcon, AddIcon, DownloadIcon } from '@chakra-ui/icons';
import { useParams, useNavigate } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import { files } from '../api/api';

const FileManagerPage = () => {
  const { domain_id } = useParams();
  const { token, currentTenant } = useContext(AuthContext);
  const navigate = useNavigate();
  const toast = useToast();

  const [fileList, setFileList] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [error, setError] = useState(null);
  const [descriptionError, setDescriptionError] = useState('');
  const [newVersionFile, setNewVersionFile] = useState(null);

  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const { isOpen: isVersionOpen, onOpen: onVersionOpen, onClose: onVersionClose } = useDisclosure();

  const [fileToDelete, setFileToDelete] = useState(null);
  const [selectedFileForVersion, setSelectedFileForVersion] = useState(null);

  useEffect(() => {
    fetchFiles();
  }, [currentTenant, domain_id, token]);

  const fetchFiles = async () => {
    setLoadingFiles(true);
    try {
      const data = await files.getAll(currentTenant, domain_id, token);
      setFileList(data);
    } catch (err) {
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

  const handleDescriptionChange = (e) => {
    setDescription(e.target.value);
    if (e.target.value.trim()) {
      setDescriptionError('');
    }
  };

  const handleAddVersion = async () => {
    if (!newVersionFile || !selectedFileForVersion) return;

    const formData = new FormData();
    formData.append('file', newVersionFile);
    formData.append('description', description);

    try {
      const newVersion = await files.upload(
        currentTenant,
        domain_id,
        formData,  // Send the complete form data
        token
      );

      toast({
        title: 'New version uploaded successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      setFileList(prevFiles =>
        prevFiles.map(file =>
          file.file_id === selectedFileForVersion.file_id
            ? { ...file, versions: [...file.versions, newVersion] }
            : file
        )
      );

      onVersionClose();
      setNewVersionFile(null);
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

    if (!description.trim()) {
      setDescriptionError('Description is required');
      return;
    }

    setUploading(true);
    try {
      const uploadedFile = await files.upload(
        currentTenant,
        domain_id,
        selectedFile,
        description.trim(),
        token
      );

      toast({
        title: 'File uploaded successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      setSelectedFile(null);
      setDescription('');
      setFileList(prevFiles => [...prevFiles, uploadedFile]);
    } catch (error) {
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

  const handleDelete = async () => {
    if (!fileToDelete) return;

    try {
      await files.delete(currentTenant, domain_id, fileToDelete.file_id, token);

      toast({
        title: 'File deleted successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      setFileList(prevFiles =>
        prevFiles.filter(file => file.file_id !== fileToDelete.file_id)
      );
      onDeleteClose();
    } catch (error) {
      toast({
        title: 'Deletion failed',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const DateFormatter = ({ dateString }) => {
    const formatDate = (date) => {
      try {
        return new Date(date).toLocaleString();
      } catch (error) {
        return 'Invalid date';
      }
    };
    return <>{formatDate(dateString)}</>;
  };

  return (
    <Box minH="100vh" bg="gray.50" py={10}>
      <Container maxW="container.xl">
        <Heading mb={8} textAlign="center">File Manager</Heading>

        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8} mb={8}>
          <Flex direction="column" gap={4}>
            <FormControl isInvalid={!!descriptionError}>
              <FormLabel>File Description</FormLabel>
              <Textarea
                value={description}
                onChange={handleDescriptionChange}
                placeholder="Enter file description"
                resize="vertical"
              />
              <FormErrorMessage>{descriptionError}</FormErrorMessage>
            </FormControl>

            <FormControl>
              <FormLabel>Select File</FormLabel>
              <Input
                type="file"
                onChange={handleFileChange}
                padding={1}
              />
            </FormControl>

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

        <Box bg="white" borderRadius="xl" boxShadow="lg" p={8}>
          <Heading size="md" mb={6}>Uploaded Files</Heading>

          {loadingFiles ? (
            <Flex justify="center" py={8}>
              <Spinner size="xl" />
            </Flex>
          ) : error ? (
            <Text color="red.500" textAlign="center" py={8}>{error}</Text>
          ) : fileList.length === 0 ? (
            <Text color="gray.500" textAlign="center" py={8}>
              No files uploaded yet
            </Text>
          ) : (
            <Accordion allowMultiple>
              {fileList.map((file) => (
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
                    <Text mb={4} color="gray.600">{file.description}</Text>
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
                        {file.versions && file.versions.map((version) => (
                          <Tr key={version.file_version_id}>
                            <Td>v{version.version_number}</Td>
                            <Td><DateFormatter dateString={version.created_at} /></Td>
                            <Td>
                              <IconButton
                                icon={<DownloadIcon />}
                                size="sm"
                                variant="ghost"
                                onClick={() => {/* Implement download */ }}
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

export default FileManagerPage;