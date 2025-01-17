from typing import Dict
import json
import os
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.models import MergeVersion, GroupVersion
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult


class GroupProcessor(BaseProcessor):
    def __init__(
        self,
        merge_version: MergeVersion,
        group_version: GroupVersion,
        config_manager: ConfigManager,
    ):
        self.merge_version = merge_version
        self.group_version = group_version
        self.system_prompt = self.group_version.system_prompt
        self.entity_group_prompt = self.group_version.entity_group_prompt
        self.custom_instructions = self.group_version.custom_instructions
        super().__init__(config_manager)

    @property
    def _get_logger_name(self) -> str:
        return f"GroupProcessor_{self.group_version.version_id}"

    @property
    def _get_output_dir(self) -> str:
        return self.group_version.output_dir

    def _analyze_groups(self, entities_data: Dict) -> Dict:
        """Analyze entity groups using the LLM"""
        self.logger.info("Analyzing entity groups")
        try:
            content = [
                {"type": "text", "text": json.dumps(entities_data)},
                {"type": "text", "text": self.entity_group_prompt},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=content),
                ]
            )

            chain = prompt | self.model
            response = chain.invoke({})
            try:
                return json.loads(response.content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse group analysis response: {str(e)}")
                raise

        except Exception as e:
            self.logger.error(f"Error in group analysis: {str(e)}")
            raise

    def process(self) -> ProcessingResult:
        try:
            self.logger.info(
                f"Starting group analysis for pipeline: {self.group_version.pipeline_id}"
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

            # Load merged entities results
            with open(self.merge_version.output_path, "r", encoding="utf-8") as f:
                merged_data = json.load(f)

            # Analyze groups
            groups_analysis = self._analyze_groups(merged_data)

            # Save analysis results
            groups_path = os.path.join(self.output_dir, "output.json")
            with open(groups_path, "w", encoding="utf-8") as f:
                json.dump(groups_analysis, f, indent=2, ensure_ascii=False)

            return ProcessingResult(
                success=True,
                status="completed",
                message="Group analysis completed successfully",
                output_path=groups_path,
            )

        except Exception as e:
            self.logger.error(f"Error during group analysis: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Group analysis failed: {str(e)}",
                error=str(e),
            )
