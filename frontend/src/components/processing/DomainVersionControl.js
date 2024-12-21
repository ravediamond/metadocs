import React from 'react';
import { Flex, Select, Badge, Text } from '@chakra-ui/react';
import { GitCommit } from 'lucide-react';

const DomainVersionControl = ({ versions, selectedVersion, onVersionChange }) => {
  return (
    <Flex 
      bg="white" 
      p="4" 
      rounded="lg" 
      shadow="sm" 
      borderWidth="1px" 
      mb="4" 
      alignItems="center" 
      gap="4"
    >
      <Flex align="center" gap="2">
        <GitCommit size={16} className="text-gray-500" />
        <Text fontWeight="medium">Domain Version:</Text>
      </Flex>
      <Select 
        w="48"
        value={selectedVersion?.version_number || ''}
        onChange={(e) => {
          const selected = versions.find(v => v.version_number === e.target.value);
          onVersionChange(selected);
        }}
      >
        {versions.map(v => (
          <option key={v.version_number} value={v.version_number}>
            {v.version_number}
          </option>
        ))}
      </Select>
      {selectedVersion && (
        <Badge 
          colorScheme={selectedVersion.status === 'Draft' ? 'green' : 'gray'}
          ml="2"
        >
          {selectedVersion.status}
        </Badge>
      )}
    </Flex>
  );
};

export default DomainVersionControl;