import React, { useEffect, useState } from 'react';
import { Flex, Select, Badge, Text } from '@chakra-ui/react';
import { GitCommit } from 'lucide-react';

const DomainVersionControl = ({ 
  domainId, 
  tenantId, 
  token, 
  domains, 
  onVersionChange 
}) => {
  const [versions, setVersions] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(null);

  useEffect(() => {
    const fetchVersions = async () => {
      try {
        const versionsData = await domains.getVersions(tenantId, domainId, token);
        console.log(versionsData);
        setVersions(versionsData);
        if (versionsData.length > 0) {
          setCurrentVersion(versionsData[0]);
          onVersionChange(versionsData[0]);
        }
      } catch (error) {
        console.error('Failed to fetch versions:', error);
      }
    };
    fetchVersions();
  }, [domainId, tenantId, token]);

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
        value={currentVersion?.version_number || ''}
        onChange={(e) => {
          const selected = versions.find(v => v.version_number === e.target.value);
          setCurrentVersion(selected);
          onVersionChange(selected);
        }}
      >
        {versions.map(v => (
          <option key={v.version_number} value={v.version_number}>
            {v.version_number}
          </option>
        ))}
      </Select>
      {currentVersion && (
        <Badge 
          colorScheme={currentVersion.status === 'Draft' ? 'green' : 'gray'}
          ml="2"
        >
          {currentVersion.status}
        </Badge>
      )}
    </Flex>
  );
};

export default DomainVersionControl;