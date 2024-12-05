import React from 'react';
import { Box, Button, Flex } from '@chakra-ui/react';
import SelectBox from './SelectBox';

const PhaseControls = ({ 
  activePhase,
  pipeline,
  files,
  selectedFile,
  selectedParsedFile,
  setSelectedFile,
  setSelectedParsedFile,
  handleStartParse,
  handleStartExtract,
  handleStartValidate,
  handleComplete,
  isLoading
}) => {
  if (pipeline?.stage === 'VALIDATE') {
    return (
      <Button
        colorScheme="blue"
        onClick={handleStartValidate}
        isLoading={isLoading}
      >
        Start Validation
      </Button>
    );
  }

  if (pipeline?.stage === 'COMPLETED') {
    return (
      <Button
        colorScheme="green"
        onClick={handleComplete}
        isLoading={isLoading}
      >
        Complete Pipeline
      </Button>
    );
  }

  switch(activePhase) {
    case 'parse':
      return (
        <Flex gap="4">
          <Box w="64">
            <SelectBox
              label="Select File"
              options={files}
              value={selectedFile}
              onChange={setSelectedFile}
              isLoading={isLoading}
            />
            {selectedFile && (
              <Button
                colorScheme="blue"
                onClick={handleStartParse}
                isLoading={isLoading}
                mt="4"
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
              options={files}
              value={selectedParsedFile}
              onChange={setSelectedParsedFile}
              isLoading={isLoading}
            />
            {selectedParsedFile && (
              <Button
                colorScheme="blue"
                onClick={handleStartExtract}
                isLoading={isLoading}
                mt="4"
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