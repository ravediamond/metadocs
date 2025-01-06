from typing import Dict
import json
import logging
import os
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.models import MergeVersion, GroupVersion, OntologyVersion
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult


class OntologyProcessor(BaseProcessor):
    def __init__(
        self,
        merge_version: MergeVersion,
        group_version: GroupVersion,
        ontology_version: OntologyVersion,
        config_manager: ConfigManager,
    ):
        self.merge_version = merge_version
        self.group_version = group_version
        self.ontology_version = ontology_version
        self.system_prompt = self.ontology_version.system_prompt
        self.ontology_prompt = self.ontology_version.ontology_prompt
        self.custom_instructions = self.ontology_version.custom_instructions
        super().__init__(config_manager)

    @property
    def _get_logger_name(self) -> str:
        return f"OntologyProcessor_{self.ontology_version.version_id}"

    @property
    def _get_output_dir(self) -> str:
        return self.ontology_version.output_dir

    def _generate_mermaid(self, entities_data: Dict, groups_data: Dict) -> str:
        """Generate Mermaid diagram using the LLM"""
        self.logger.info("Generating Mermaid diagram")
        try:
            content = [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"entities": entities_data, "groups": groups_data}
                    ),
                },
                {"type": "text", "text": self.ontology_prompt},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=content),
                ]
            )

            chain = prompt | self.model
            response = chain.invoke({})
            return response.content

        except Exception as e:
            self.logger.error(f"Error generating Mermaid diagram: {str(e)}")
            raise

    def process(self) -> ProcessingResult:
        try:
            self.logger.info(
                f"Starting ontology generation for pipeline: {self.ontology_version.pipeline_id}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            # Verify merge version output exists
            if not os.path.exists(self.merge_version.output_path):
                error_msg = (
                    f"Merge output file not found: {self.merge_version.output_path}"
                )
                self.logger.error(error_msg)
                return ProcessingResult(
                    success=False, status="failed", message=error_msg, error=error_msg
                )

            # Verify group version output exists
            if not os.path.exists(self.group_version.output_path):
                error_msg = (
                    f"Group output file not found: {self.group_version.output_path}"
                )
                self.logger.error(error_msg)
                return ProcessingResult(
                    success=False, status="failed", message=error_msg, error=error_msg
                )

            # Load the data from the version outputs
            with open(self.merge_version.output_path, "r", encoding="utf-8") as f:
                try:
                    entities_data = json.load(f)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse merge output JSON: {str(e)}"
                    self.logger.error(error_msg)
                    return ProcessingResult(
                        success=False,
                        status="failed",
                        message=error_msg,
                        error=error_msg,
                    )

            with open(self.group_version.output_path, "r", encoding="utf-8") as f:
                try:
                    groups_data = json.load(f)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse group output JSON: {str(e)}"
                    self.logger.error(error_msg)
                    return ProcessingResult(
                        success=False,
                        status="failed",
                        message=error_msg,
                        error=error_msg,
                    )

            # Generate Mermaid diagram
            mermaid_diagram = self._generate_mermaid(entities_data, groups_data)

            # Save the diagram
            diagram_path = os.path.join(self.output_dir, "output.json")
            with open(diagram_path, "w", encoding="utf-8") as f:
                f.write(mermaid_diagram)

            return ProcessingResult(
                success=True,
                status="completed",
                message="Ontology diagram generated successfully",
                data={"mermaid": mermaid_diagram},
                output_path=diagram_path,
            )

        except Exception as e:
            self.logger.error(f"Error generating ontology: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Ontology generation failed: {str(e)}",
                error=str(e),
            )
