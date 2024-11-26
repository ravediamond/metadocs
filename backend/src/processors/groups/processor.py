# src/processors/groups/processor.py

from dataclasses import dataclass
from typing import Dict, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ...models.models import ProcessingPipeline
from ...core.config import ConfigManager
from ..prompts.group_prompts import SYSTEM_PROMPT, GROUP_ANALYSIS_PROMPT
from ...llm.llm_factory import LLMConfig, LLMFactory


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    groups_path: Optional[str] = None


class GroupProcessor:
    def __init__(self, pipeline: ProcessingPipeline, config: ConfigManager):
        self.pipeline = pipeline
        self.config = config
        self.output_dir = os.path.join(
            self.config.get("processing_dir", "processing_output"),
            str(self.pipeline.domain_id),
            "groups",
        )
        self.logger = self._setup_logger()
        self.model = self._setup_model()

    def _setup_model(self) -> ChatBedrock:
        """Initialize the LLM model"""
        llm_config = LLMConfig(
            provider=self.config.get("llm_provider", "bedrock"),
            profile_name=self.config.get("aws_profile"),
            model_id=self.config.get(
                "aws_model_id", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            model_kwargs={
                "temperature": float(self.config.get("llm_temperature", 0)),
                "max_tokens": int(self.config.get("llm_max_tokens", 4096)),
            },
        )
        return LLMFactory(llm_config).create_model()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"GroupProcessor_{self.pipeline.pipeline_id}")
        logger.setLevel(logging.DEBUG)
        os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)

        file_handler = logging.FileHandler(
            os.path.join(
                self.output_dir,
                "logs",
                f"group_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            )
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def _analyze_groups(self, entities_data: Dict) -> Dict:
        self.logger.info("Analyzing entity groups")
        try:
            content = [
                {"type": "text", "text": json.dumps(entities_data)},
                {"type": "text", "text": GROUP_ANALYSIS_PROMPT},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
            )

            chain = prompt | self.model
            response = chain.invoke({})
            return json.loads(response.content)

        except Exception as e:
            self.logger.error(f"Error in group analysis: {str(e)}")
            raise

    def process(self) -> ProcessingResult:
        try:
            self.logger.info(
                f"Starting group analysis for pipeline: {self.pipeline.pipeline_id}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            # Load merged entities results
            merge_version = next(
                (
                    v
                    for v in self.pipeline.merge_versions
                    if v.version_id == self.pipeline.current_merge_id
                ),
                None,
            )

            if not merge_version or not merge_version.output_path:
                raise ValueError("No merged entities data available")

            # Load merged entities results
            with open(merge_version.output_path, "r", encoding="utf-8") as f:
                merged_data = json.load(f)

            # Analyze groups
            groups_analysis = self._analyze_groups(merged_data)

            # Save analysis results
            groups_path = os.path.join(self.output_dir, "groups.json")
            with open(groups_path, "w", encoding="utf-8") as f:
                json.dump(groups_analysis, f, indent=2, ensure_ascii=False)

            return ProcessingResult(
                success=True,
                message="Group analysis completed successfully",
                data=groups_analysis,
                groups_path=groups_path,
            )

        except Exception as e:
            self.logger.error(f"Error during group analysis: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False, message=f"Group analysis failed: {str(e)}"
            )
