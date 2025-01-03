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

const ChatPanel = ({
  parseVersions = [],
  extractVersions = [],
  mergeVersionId = null,
  groupVersionId = null,
  ontologyVersionId = null,
  pipeline = null
}) => {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const { token, currentTenant } = useContext(AuthContext);
  const { domain_id } = useParams();
  const toast = useToast();

  console.log('ChatPanel input props:', {
    parseVersions,
    extractVersions,
    mergeVersionId,
    groupVersionId,
    ontologyVersionId,
    pipeline: pipeline?.pipeline_id ? {
      id: pipeline.pipeline_id,
      stage: pipeline.stage,
      status: pipeline.status,
      latest_versions: {
        parse: pipeline.latest_parse_version_id,
        extract: pipeline.latest_extract_version_id,
        merge: pipeline.latest_merge_version_id,
        group: pipeline.latest_group_version_id,
        ontology: pipeline.latest_ontology_version_id
      }
    } : null
  });

  const formatAssistantResponse = (analysis) => {
    let content = [];

    if (analysis.intent) {
      content.push(`Intent: ${analysis.intent}`);
    }

    content.push(analysis.response);

    if (analysis.suggestions?.length > 0) {
      content.push('\nSuggestions:');
      content.push(analysis.suggestions.map(s => `• ${s}`).join('\n'));
    }

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
        warnings: analysis.warnings
      }
    };
  };

  const getCurrentVersions = () => {
    // Pipeline completed - return all versions
    if (pipeline?.status === 'COMPLETED') {
      console.log('Pipeline completed, sending all versions:', {
        parseVersions,
        extractVersions,
        mergeVersionId,
        groupVersionId,
        ontologyVersionId
      });
      return {
        parseVersions,
        extractVersions,
        mergeVersionId,
        groupVersionId,
        ontologyVersionId
      };
    }

    // No pipeline or not completed - use stage-based logic
    const currentStage = pipeline?.stage?.toLowerCase();
    const stages = ['parse', 'extract', 'merge', 'group', 'ontology'];
    const stageIndex = stages.indexOf(currentStage);

    const versions = {
      parseVersions: stageIndex >= 0 ? parseVersions : [],
      extractVersions: stageIndex >= 1 ? extractVersions : [],
      mergeVersionId: stageIndex >= 2 ? mergeVersionId : null,
      groupVersionId: stageIndex >= 3 ? groupVersionId : null,
      ontologyVersionId: stageIndex >= 4 ? ontologyVersionId : null
    };

    console.log('Stage-based versions:', versions);
    return versions;
  };

  const handleSend = async () => {
    if (!message.trim()) return;

    try {
      setIsLoading(true);

      const userMessage = { role: 'user', content: message };
      setMessages(prev => [...prev, userMessage]);

      const versions = getCurrentVersions();
      console.log('Sending versions to backend:', versions);

      const analysis = await chat.analyzeQuery(
        currentTenant,
        domain_id,
        message,
        token,
        versions
      );

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

      <Box flex="1" overflowY="auto" p="4">
        <VStack spacing="4" align="stretch">
          {messages.length === 0 && (
            <Box bg="blue.50" rounded="lg" p="3">
              <Text fontSize="sm">
                I can help you understand and analyze the processing results.
                Ask me about:
                • Document parsing status
                • Extracted entities
                • Entity groups
                • Ontology structure
                • Processing errors

                What would you like to know?
              </Text>
            </Box>
          )}

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