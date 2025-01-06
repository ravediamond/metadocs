import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Box, useColorModeValue } from '@chakra-ui/react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

const MarkdownVisualization = ({ content }) => {
    const bgColor = useColorModeValue('white', 'gray.800');

    if (!content) {
        return null;
    }

    return (
        <Box
            p={6}
            bg={bgColor}
            className="markdown-content"
            overflow="auto"
            sx={{
                '& h1': { fontSize: '2xl', fontWeight: 'bold', mb: 4, mt: 6 },
                '& h2': { fontSize: 'xl', fontWeight: 'bold', mb: 3, mt: 5 },
                '& h3': { fontSize: 'lg', fontWeight: 'bold', mb: 2, mt: 4 },
                '& p': { mb: 4 },
                '& ul, & ol': { mb: 4, pl: 6 },
                '& li': { mb: 1 },
                '& code': {
                    px: 2,
                    py: 1,
                    bg: 'gray.100',
                    borderRadius: 'md',
                    fontSize: 'sm',
                },
                '& pre': {
                    mb: 4,
                    borderRadius: 'md',
                    overflow: 'auto',
                },
            }}
        >
            <ReactMarkdown
                components={{
                    code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                            <SyntaxHighlighter
                                style={tomorrow}
                                language={match[1]}
                                PreTag="div"
                                {...props}
                            >
                                {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                        ) : (
                            <code className={className} {...props}>
                                {children}
                            </code>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </Box>
    );
};

export default MarkdownVisualization;