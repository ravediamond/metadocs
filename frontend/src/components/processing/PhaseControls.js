import React from 'react';
import { Box, Button, Flex } from '@chakra-ui/react';
import SelectBox from './SelectBox';

const PhaseControls = ({ 
  activePhase,
  files,
  parsedFiles,
  versions,
  selectedFile,
  selectedParsedFile,
  selectedVersion,
  setSelectedFile,
  setSelectedParsedFile,
  setSelectedVersion,
  handleStartParse,
  handleStartExtract,
  isLoading
}) => {
  const fileVersions = files.map(file => ({
    value: file.version_number,
    label: `File Version ${file.version_number}`
  }));

  switch(activePhase) {
    case 'parse':
      return (
        <Flex gap="4">
          <Box w="64">
            <SelectBox
              label="File Version"
              options={fileVersions}
              value={selectedVersion}
              onChange={setSelectedVersion}
              isLoading={isLoading}
            />
            {selectedVersion && (
              <Button
                colorScheme="blue"
                onClick={handleStartParse}
                isLoading={isLoading}
              >
                Start Parsing
              </Button>
            )}
          </Box>
        </Flex>
      );
    case 'extract':
      return (
        <Flex gap="4">
          <Box w="64">
            <SelectBox
              label="Select Parsed File"
              options={parsedFiles}
              value={selectedParsedFile}
              onChange={setSelectedParsedFile}
              isLoading={isLoading}
            />
            {selectedParsedFile && (
              <Button
                colorScheme="blue"
                onClick={handleStartExtract}
                isLoading={isLoading}
              >
                Start Extraction
              </Button>
            )}
          </Box>
        </Flex>
      );
    default:
      return null;
  }
};

export default PhaseControls;