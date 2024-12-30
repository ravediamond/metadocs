import React from "react";
import { Box, Flex, Text, Spinner, Heading } from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";
import MermaidDiagram from "./MermaidDiagram";
import ForceGraph from "./ForceGraph";

const StageDetailPanel = ({ stage, files, results, isLoading }) => {
    const renderContent = () => {
        if (isLoading) {
            return (
                <Flex justify="center" align="center" height="100%">
                    <Spinner />
                </Flex>
            );
        }

        if (!results) {
            return (
                <Flex justify="center" align="center" height="100%">
                    <Text>No results available</Text>
                </Flex>
            );
        }

        switch (stage.id) {
            case "parse":
                return (
                    <Box overflowY="auto" p={4}>
                        <ReactMarkdown>{results}</ReactMarkdown>
                    </Box>
                );
            case "extract":
            case "merge":
            case "group":
                return (
                    <Box overflowY="auto" p={4} height="100%">
                        <ForceGraph data={results} />
                    </Box>
                );
            case "ontology":
                return <MermaidDiagram diagram={results} />;
            default:
                return (
                    <Flex justify="center" align="center" height="100%">
                        <Text>Unsupported stage type</Text>
                    </Flex>
                );
        }
    };

    return (
        <Box
            borderWidth="1px"
            borderRadius="lg"
            bg="white"
            height="calc(100vh - 400px)"
            overflow="hidden"
        >
            <Flex
                px={6}
                py={4}
                borderBottomWidth="1px"
                align="center"
                justify="space-between"
            >
                <Heading size="md">{stage.label} Results</Heading>
            </Flex>

            <Box height="calc(100% - 60px)" overflowY="auto">
                {renderContent()}
            </Box>
        </Box>
    );
};

export default StageDetailPanel;