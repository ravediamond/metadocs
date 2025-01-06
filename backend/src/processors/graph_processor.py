from typing import Dict, List, Optional
import json
import os
from datetime import datetime
from time import time
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from ..models.models import GraphVersion, ExtractVersion
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult
from .prompts.graph_prompts import (
    SYSTEM_PROMPT,
    ENTITY_ANALYSIS_PROMPT,
    VISUALIZATION_PROMPT,
    VALIDATION_PROMPT,
    UPDATE_PROMPT,
)


class GraphProcessor(BaseProcessor):
    def __init__(
        self,
        extract_versions: List[ExtractVersion],
        graph_version: GraphVersion,
        config_manager: ConfigManager,
    ):
        self.extract_versions = extract_versions
        self.graph_version = graph_version
        self.system_prompt = SYSTEM_PROMPT
        super().__init__(config_manager)

    @property
    def _get_logger_name(self) -> str:
        return f"GraphProcessor_{self.graph_version.version_id}"

    @property
    def _get_output_dir(self) -> str:
        return self.graph_version.output_dir

    def _load_extracted_data(self) -> List[Dict]:
        """Load and combine data from all extract versions"""
        all_data = []
        for version in self.extract_versions:
            try:
                with open(version.output_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_data.append(data)
            except Exception as e:
                self.logger.error(
                    f"Error loading extract version {version.version_id}: {e}"
                )
                raise
        return all_data

    def _analyze_entities(self, extracted_data: List[Dict]) -> Dict:
        """Analyze and combine extracted entities into a unified graph"""
        try:
            content = [
                {"type": "text", "text": json.dumps(extracted_data)},
                {"type": "text", "text": ENTITY_ANALYSIS_PROMPT},
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=content),
                ]
            )
            chain = prompt | self.model
            response = chain.invoke({})
            return json.loads(response.content)
        except Exception as e:
            self.logger.error(f"Error in entity analysis: {e}")
            raise

    def _generate_visualization(self, graph_data: Dict) -> Dict:
        """Generate visualization for the graph"""
        try:
            content = [
                {"type": "text", "text": json.dumps(graph_data)},
                {"type": "text", "text": VISUALIZATION_PROMPT},
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=content),
                ]
            )
            chain = prompt | self.model
            response = chain.invoke({})
            return json.loads(response.content)
        except Exception as e:
            self.logger.error(f"Error generating visualization: {e}")
            raise

    def _validate_graph(self, graph_data: Dict) -> List[str]:
        """Validate the generated graph"""
        try:
            content = [
                {"type": "text", "text": json.dumps(graph_data)},
                {"type": "text", "text": VALIDATION_PROMPT},
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=content),
                ]
            )
            chain = prompt | self.model
            response = chain.invoke({})
            validation_result = json.loads(response.content)
            return validation_result.get("validation_errors", [])
        except Exception as e:
            self.logger.error(f"Error in graph validation: {e}")
            raise

    def update_graph(self, current_graph: Dict, feedback: str) -> Dict:
        """Update the graph based on feedback"""
        try:
            content = [
                {
                    "type": "text",
                    "text": UPDATE_PROMPT.format(
                        current_graph=json.dumps(current_graph), feedback=feedback
                    ),
                },
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=content),
                ]
            )
            chain = prompt | self.model
            response = chain.invoke({})
            return json.loads(response.content)
        except Exception as e:
            self.logger.error(f"Error updating graph: {e}")
            raise

    def process(self) -> ProcessingResult:
        """Process extracted data into a knowledge graph"""
        try:
            self.logger.info(
                f"Starting graph processing for version {self.graph_version.version_id}"
            )

            # Load and combine extracted data
            extracted_data = self._load_extracted_data()

            # Analyze entities and create graph
            graph_data = self._analyze_entities(extracted_data)

            # Generate visualization
            visualization = self._generate_visualization(graph_data)

            # Validate graph
            validation_errors = self._validate_graph(graph_data)

            # Combine results
            result = {
                "graph": graph_data,
                "visualization": visualization,
                "metadata": {
                    "entity_count": len(graph_data.get("entities", [])),
                    "relationship_count": len(graph_data.get("relationships", [])),
                    "group_count": len(graph_data.get("groups", [])),
                    "validation_errors": validation_errors,
                    "processed_at": self.graph_version.created_at.isoformat(),
                    "source_versions": [
                        str(v.version_id) for v in self.extract_versions
                    ],
                },
            }

            # Save results
            output_path = os.path.join(self.output_dir, "output.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Save visualization separately for easier access
            viz_path = os.path.join(self.output_dir, "visualization.json")
            with open(viz_path, "w", encoding="utf-8") as f:
                json.dump(visualization, f, indent=2, ensure_ascii=False)

            self.logger.info("Graph processing completed successfully")
            return ProcessingResult(
                success=True,
                status="completed",
                message="Graph processing completed successfully",
                data=result,
                output_path=output_path,
            )

        except Exception as e:
            self.logger.error(f"Error during graph processing: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Graph processing failed: {str(e)}",
                error=str(e),
            )

    async def process_feedback(self, feedback: str) -> ProcessingResult:
        """Process feedback and update the graph"""
        try:
            self.logger.info(
                f"Processing feedback for graph version {self.graph_version.version_id}"
            )

            # Load current graph
            with open(self.graph_version.output_path, "r", encoding="utf-8") as f:
                current_graph = json.load(f)

            # Update graph based on feedback
            updated_graph = self.update_graph(current_graph["graph"], feedback)

            # Generate new visualization
            visualization = self._generate_visualization(updated_graph)

            # Validate updated graph
            validation_errors = self._validate_graph(updated_graph)

            # Combine results
            result = {
                "graph": updated_graph,
                "visualization": visualization,
                "metadata": {
                    "entity_count": len(updated_graph.get("entities", [])),
                    "relationship_count": len(updated_graph.get("relationships", [])),
                    "group_count": len(updated_graph.get("groups", [])),
                    "validation_errors": validation_errors,
                    "processed_at": self.graph_version.created_at.isoformat(),
                    "source_versions": [
                        str(v.version_id) for v in self.extract_versions
                    ],
                    "feedback_processed": True,
                    "feedback_timestamp": datetime.utcnow().isoformat(),
                },
            }

            # Save updated results
            feedback_path = os.path.join(
                self.output_dir, f"feedback_{int(time.time())}.json"
            )
            with open(feedback_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            self.logger.info("Feedback processing completed successfully")
            return ProcessingResult(
                success=True,
                status="completed",
                message="Feedback processing completed successfully",
                data=result,
                output_path=feedback_path,
            )

        except Exception as e:
            self.logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Feedback processing failed: {str(e)}",
                error=str(e),
            )
