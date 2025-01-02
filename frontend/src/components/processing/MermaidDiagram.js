import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';
import { Box, Text, Alert, AlertIcon, AlertTitle, AlertDescription } from '@chakra-ui/react';

export const MermaidDiagram = ({ diagram }) => {
    const containerRef = useRef(null);

    useEffect(() => {
        if (!diagram) {
            console.log('No diagram content provided');
            return;
        }

        // Initialize mermaid with custom config
        mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            themeVariables: {
                fontFamily: 'Inter',
            },
            flowchart: {
                htmlLabels: true,
                curve: 'basis'
            }
        });

        const renderDiagram = async () => {
            try {
                // Validate diagram content
                if (diagram === '') {
                    throw new Error('Empty diagram content');
                }

                // Clear previous content
                if (containerRef.current) {
                    containerRef.current.innerHTML = '';

                    // Create unique ID for this diagram
                    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

                    // Generate SVG
                    const { svg } = await mermaid.render(id, diagram);

                    // Set the generated SVG
                    containerRef.current.innerHTML = svg;

                    // Make the diagram zoomable/pannable
                    const svgElement = containerRef.current.querySelector('svg');
                    if (svgElement) {
                        svgElement.style.width = '100%';
                        svgElement.style.height = '100%';
                        svgElement.style.maxHeight = '800px';
                    }
                }
            } catch (error) {
                console.error('Error rendering mermaid diagram:', error);
                if (containerRef.current) {
                    // Use Chakra UI Alert component for error display
                    containerRef.current.innerHTML = '';
                    const errorAlert = document.createElement('div');
                    errorAlert.innerHTML = `
                        <div role="alert" class="chakra-alert css-1rr4qq7">
                            <span class="chakra-alert__icon css-1c6vscd">
                                <svg viewBox="0 0 24 24" class="chakra-icon css-13otjrl" focusable="false" aria-hidden="true">
                                    <path fill="currentColor" d="M11.983,0a12.206,12.206,0,0,0-8.51,3.653A11.8,11.8,0,0,0,0,12.207,11.779,11.779,0,0,0,11.8,24h.214A12.111,12.111,0,0,0,24,11.791h0A11.766,11.766,0,0,0,11.983,0ZM10.5,16.542a1.476,1.476,0,0,1,1.449-1.53h.027a1.527,1.527,0,0,1,1.523,1.47,1.475,1.475,0,0,1-1.449,1.53h-.027A1.529,1.529,0,0,1,10.5,16.542ZM11,12.5v-6a1,1,0,0,1,2,0v6a1,1,0,1,1-2,0Z"></path>
                                </svg>
                            </span>
                            <div class="chakra-alert__content css-1s88wk3">
                                <div class="chakra-alert__title css-1qvyk2p">Error rendering diagram:</div>
                                <div class="chakra-alert__desc css-1gu2qsf">${error.message}</div>
                            </div>
                        </div>
                    `;
                    containerRef.current.appendChild(errorAlert);
                }
            }
        };

        renderDiagram();
    }, [diagram]);

    if (!diagram) {
        return (
            <Box p={4} textAlign="center">
                <Text color="gray.500">No diagram available</Text>
            </Box>
        );
    }

    return (
        <Box className="relative w-full h-full min-h-[500px]">
            <div
                ref={containerRef}
                className="w-full h-full overflow-auto bg-white rounded-lg shadow p-4"
            />
        </Box>
    );
};

export default MermaidDiagram;