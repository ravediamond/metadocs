import React, { useState, useCallback } from 'react';
import { Box, VStack, Input, Button, Text, Alert, AlertIcon } from '@chakra-ui/react';
import { chat } from '../../api/api';
import { useAuth } from '../../context/AuthContext';
import { useParams } from 'react-router-dom';

const ChatPanel = ({
  parseVersions,
  extractVersions,
  graphVersionId, // Changed from merge/group/ontology versions
  pipeline,
  onVisualizationUpdate
}) => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const { token, currentTenant } = useAuth();
  const { domain_id } = useParams();

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      setIsLoading(true);
      const response = await chat.analyzeQuery(
        currentTenant,
        domain_id,
        query,
        token,
        {
          parseVersions,
          extractVersions,
          graphVersionId, // Simplified versions object
        }
      );

      // Add user message
      setMessages(prev => [...prev, { sender: 'user', content: query }]);

      // Add assistant response
      setMessages(prev => [...prev, {
        sender: 'assistant',
        content: response.response,
        visualization: response.visualization
      }]);

      // Update visualization if provided
      if (response.visualization) {
        onVisualizationUpdate(response.visualization);
      }

      setQuery('');
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        sender: 'system',
        content: `Error: ${error.message}`,
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [query, currentTenant, domain_id, token, parseVersions, extractVersions, graphVersionId, onVisualizationUpdate]);

  return (
    <Box h="full" bg="white" rounded="lg" shadow="sm" p={4}>
      <VStack h="full" spacing={4}>
        <Box flex={1} w="full" overflowY="auto">
          {messages.map((message, index) => (
            <Box
              key={index}
              mb={4}
              p={3}
              bg={message.sender === 'user' ? 'blue.50' : 'gray.50'}
              rounded="md"
            >
              {message.isError ? (
                <Alert status="error">
                  <AlertIcon />
                  {message.content}
                </Alert>
              ) : (
                <>
                  <Text fontWeight="bold" mb={1}>
                    {message.sender === 'user' ? 'You' : 'Assistant'}:
                  </Text>
                  <Text>{message.content}</Text>
                </>
              )}
            </Box>
          ))}
        </Box>

        <form onSubmit={handleSubmit} style={{ width: '100%' }}>
          <Box display="flex" gap={2}>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question or give instructions..."
              disabled={isLoading}
            />
            <Button
              type="submit"
              colorScheme="blue"
              isLoading={isLoading}
            >
              Send
            </Button>
          </Box>
        </form>
      </VStack>
    </Box>
  );
};

export default ChatPanel;