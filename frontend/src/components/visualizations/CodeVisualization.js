import React from 'react';
import { Box } from '@chakra-ui/react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const CodeVisualization = ({ code, language = 'javascript' }) => {
    // Custom dark theme
    const customStyle = {
        ...vscDarkPlus,
        'pre[class*="language-"]': {
            ...vscDarkPlus['pre[class*="language-"]'],
            background: '#1E1E1E', // Dark gray background
            margin: 0,
        },
        'code[class*="language-"]': {
            ...vscDarkPlus['code[class*="language-"]'],
            background: '#1E1E1E', // Dark gray background
        }
    };

    if (!code) {
        return null;
    }

    return (
        <Box
            bg="#1E1E1E"
            borderRadius="md"
            overflow="auto"
            maxH="800px"
            sx={{
                '& pre': {
                    margin: '0 !important',
                    borderRadius: 'md',
                }
            }}
        >
            <SyntaxHighlighter
                language={language}
                style={customStyle}
                customStyle={{
                    margin: 0,
                    padding: '1.5rem',
                    backgroundColor: '#1E1E1E',
                    fontSize: '14px',
                    lineHeight: '1.5',
                }}
                wrapLines={true}
                wrapLongLines={true}
            >
                {code}
            </SyntaxHighlighter>
        </Box>
    );
};

export default CodeVisualization;