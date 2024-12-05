import React from 'react';
import { Box, Select, Text } from '@chakra-ui/react';

const SelectBox = ({ label, options, value, onChange, isLoading }) => (
  <Box mb="4">
    <Text fontSize="sm" fontWeight="medium" color="gray.700" mb="1">
      {label}
    </Text>
    <Select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      bg="white"
      p="2"
      focusBorderColor="blue.500"
      isDisabled={isLoading}
    >
      <option value="">Select {label.toLowerCase()}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </Select>
  </Box>
);

export default SelectBox;