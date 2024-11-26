import React, { useState, useRef, useEffect } from 'react';
import {
    Box,
    VStack,
    Input,
    Button,
    Text,
    Flex,
    Avatar,
    Divider,
} from '@chakra-ui/react';

const ChatPanel = ({ domainId, currentStage }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = () => {
        if (!input.trim()) return;

        const newMessage = {
            id: Date.now(),
            text: input,
            sender: 'user',
            timestamp: new Date(),
        };

        setMessages([...messages, newMessage]);

        // Simulate AI response
        setTimeout(() => {
            const aiResponse = {
                id: Date.now() + 1,
                text: `Processing response for ${currentStage.name}...`,
                sender: 'ai',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, aiResponse]);
        }, 1000);

        setInput('');
    };

    return (
        <Box
            bg="white"
            borderRadius="lg"
            shadow="sm"
            h="calc(100vh - 200px)"
            position="relative"
        >
            <Box p={4} borderBottom="1px" borderColor="gray.200">
                <Text fontWeight="bold">Processing Assistant</Text>
            </Box>

            <VStack
                spacing={4}
                p={4}
                overflowY="auto"
                h="calc(100% - 140px)"
                align="stretch"
            >
                {messages.map((message) => (
                    <Flex
                        key={message.id}
                        justify={message.sender === 'user' ? 'flex-end' : 'flex-start'}
                    >
                        <Box
                            maxW="80%"
                            bg={message.sender === 'user' ? 'blue.500' : 'gray.100'}
                            color={message.sender === 'user' ? 'white' : 'black'}
                            borderRadius="lg"
                            p={3}
                        >
                            <Text>{message.text}</Text>
                        </Box>
                    </Flex>
                ))}
                <div ref={messagesEndRef} />
            </VStack>

            <Box p={4} position="absolute" bottom={0} left={0} right={0}>
                <Flex>
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a question..."
                        mr={2}
                    />
                    <Button colorScheme="blue" onClick={handleSend}>
                        Send
                    </Button>
                </Flex>
            </Box>
        </Box>
    );
};

export default ChatPanel;