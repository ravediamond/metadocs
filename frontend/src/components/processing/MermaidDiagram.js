import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';
import { Box, Text } from '@chakra-ui/react';

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
                    containerRef.current.innerHTML = `
            <div class="text-red-500 p-4">
              Error rendering diagram: ${error.message}
            </div>
          `;
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
                className="w-full h-full overflow-auto bg-white rounded-lg shadow"
            />
        </Box>
    );
};

export default MermaidDiagram;