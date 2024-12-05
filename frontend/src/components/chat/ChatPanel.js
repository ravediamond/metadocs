import React, { useState } from 'react';
import {
  Box,
  Button,
  Flex,
  Icon,
  Input,
  Text,
} from '@chakra-ui/react';
import { MessageSquare, Settings } from 'lucide-react';

const ChatPanel = () => {
  const [message, setMessage] = useState('');

  return (
    <Flex w="96" bg="white" borderLeftWidth="1px" direction="column">
      <Flex p="4" borderBottomWidth="1px" align="center" justify="space-between">
        <Flex align="center" gap="2">
          <Icon as={MessageSquare} boxSize="5" color="blue.500" />
          <Text fontWeight="medium">Knowledge Assistant</Text>
        </Flex>
        <Icon
          as={Settings}
          boxSize="5"
          color="gray.400"
          cursor="pointer"
          _hover={{ color: 'gray.600' }}
        />
      </Flex>

      <Box flex="1" overflowY="auto" p="4" spacing="4">
        <Box bg="blue.50" rounded="lg" p="3" ml="8">
          <Text fontSize="sm">
            I can help you with:
            - Creating new versions
            - Modifying prompts
            - Analyzing results
            - Starting next phases
            
            What would you like to do?
          </Text>
        </Box>
      </Box>

      <Box p="4" borderTopWidth="1px">
        <Flex gap="2">
          <Input
            placeholder="Type your message..."
            p="3"
            focusBorderColor="blue.500"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <Button colorScheme="blue">
            Send
          </Button>
        </Flex>
      </Box>
    </Flex>
  );
};

export default ChatPanel;