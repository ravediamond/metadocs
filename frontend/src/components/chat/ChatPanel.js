import React, { useState, useContext } from 'react';
import {
  Box,
  Button,
  Flex,
  Icon,
  Input,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { MessageSquare, Settings } from 'lucide-react';
import { chat } from '../../api/api';
import AuthContext from '../../context/AuthContext';
import { useParams } from 'react-router-dom';

const ChatPanel = () => {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const { token, currentTenant } = useContext(AuthContext);
  const { domain_id } = useParams();
  const toast = useToast();

  const formatAssistantResponse = (analysis) => {
    let content = [];

    // Add intent if present
    if (analysis.intent) {
      content.push(`Intent: ${analysis.intent}`);
    }

    // Add main response
    content.push(analysis.response);

    // Add suggestions if present
    if (analysis.suggestions?.length > 0) {
      content.push('\nSuggestions:');
      content.push(analysis.suggestions.map(s => `• ${s}`).join('\n'));
    }

    // Add todo list if present
    if (analysis.todo_list?.length > 0) {
      content.push('\nNext steps:');
      content.push(analysis.todo_list.map(t => `• ${t}`).join('\n'));
    }

    // Add warnings if present
    if (analysis.warnings?.length > 0) {
      content.push('\nWarnings:');
      content.push(analysis.warnings.map(w => `• ${w}`).join('\n'));
    }

    return {
      role: 'assistant',
      content: content.join('\n'),
      metadata: {
        messageType: analysis.message_type,
        intent: analysis.intent,
        suggestions: analysis.suggestions,
        todoList: analysis.todo_list,
        warnings: analysis.warnings
      }
    };
  };

  const handleSend = async () => {
    if (!message.trim()) return;

    try {
      setIsLoading(true);

      // Add user message to chat
      const userMessage = { role: 'user', content: message };
      setMessages(prev => [...prev, userMessage]);

      // Analyze the query with version information
      const analysis = await chat.analyzeQuery(
        currentTenant,
        domain_id,
        message,
        token,
        {
          parseVersions: {},
          extractVersions: {},
          mergeVersionId: null,
          groupVersionId: null,
          ontologyVersionId: null
        }
      );

      // Format and add assistant message
      const assistantMessage = formatAssistantResponse(analysis);
      setMessages(prev => [...prev, assistantMessage]);
      setMessage('');

    } catch (error) {
      console.error('Error processing message:', error);
      toast({
        title: 'Error processing message',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Flex
      direction="column"
      h="full"
      bg="white"
      borderWidth="1px"
      borderColor="gray.200"
      rounded="lg"
      shadow="sm"
    >
      {/* Header */}
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

      {/* Messages Area */}
      <Box flex="1" overflowY="auto" p="4">
        <VStack spacing="4" align="stretch">
          {/* Initial welcome message */}
          {messages.length === 0 && (
            <Box bg="blue.50" rounded="lg" p="3">
              <Text fontSize="sm">
                I can help you with:
                - Creating new versions
                - Modifying prompts
                - Analyzing results
                - Starting next phases

                What would you like to do?
              </Text>
            </Box>
          )}

          {/* Chat messages */}
          {messages.map((msg, idx) => (
            <Box
              key={idx}
              bg={msg.role === 'user' ? 'gray.100' : 'blue.50'}
              rounded="lg"
              p="3"
              ml={msg.role === 'user' ? '0' : '4'}
              mr={msg.role === 'user' ? '4' : '0'}
            >
              <Text fontSize="sm" whiteSpace="pre-wrap">
                {msg.content}
              </Text>
            </Box>
          ))}
        </VStack>
      </Box>

      {/* Input Area */}
      <Box p="4" borderTopWidth="1px">
        <Flex gap="2">
          <Input
            placeholder="Type your message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isLoading}
          />
          <Button
            colorScheme="blue"
            onClick={handleSend}
            isLoading={isLoading}
          >
            Send
          </Button>
        </Flex>
      </Box>
    </Flex>
  );
};

export default ChatPanel;