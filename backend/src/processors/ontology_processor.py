from typing import Dict
import json
import logging
from datetime import datetime
import os
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.models import MergeVersion, GroupVersion
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult


class OntologyProcessor(BaseProcessor):
    def __init__(
        self,
        merge_version: MergeVersion,
        group_version: GroupVersion,
        ontology_version: GroupVersion,
        config_manager: ConfigManager,
    ):
        self.merge_version = merge_version
        self.group_version = group_version
        self.ontology_version = ontology_version
        self.system_prompt = self.ontology_version.system_prompt
        self.ontology_prompt = self.ontology_version.ontology_prompt
        # TODO: Implement custom instructions
        self.custom_instructions = self.ontology_version.custom_instructions
        super().__init__(config_manager)

    def _generate_mermaid(self, entities_data: Dict, groups_data: Dict) -> str:
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

            merge_version = next(
                (
                    v
                    for v in self.ontology_version.merge_versions
                    if v.version_id == self.ontology_version.current_merge_id
                ),
                None,
            )
            if not merge_version or not merge_version.output_path:
                raise ValueError("No merged entities data available")

            group_version = next(
                (
                    v
                    for v in self.ontology_version.group_versions
                    if v.version_id == self.ontology_version.current_group_id
                ),
                None,
            )
            if not group_version or not group_version.output_path:
                raise ValueError("No group data available")

            # Load the data from the version outputs
            with open(merge_version.output_path, "r", encoding="utf-8") as f:
                entities_data = json.load(f)

            with open(group_version.output_path, "r", encoding="utf-8") as f:
                groups_data = json.load(f)

            mermaid_diagram = self._generate_mermaid(entities_data, groups_data)

            diagram_path = os.path.join(self.output_dir, "ontology.json")
            with open(diagram_path, "w", encoding="utf-8") as f:
                f.write(mermaid_diagram)

            return ProcessingResult(
                success=True,
                status="completed",
                message="Ontology diagram generated successfully",
                data={"mermaid": mermaid_diagram},
                diagram_path=diagram_path,
            )

        except Exception as e:
            self.logger.error(f"Error generating ontology: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Ontology generation failed: {str(e)}",
                error=str(e),
            )
