from dataclasses import dataclass
from typing import Dict, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.models import MergeVersion, GroupVersion
from ..core.config import ConfigManager, FILE_SYSTEM
from ..llm.llm_factory import LLMConfig, LLMFactory


@dataclass
class ProcessingResult:
    success: bool
    status: str
    message: str
    error: str


class GroupProcessor:
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
        # TODO: Implement custom instructions
        self.custom_instructions = self.group_version.custom_instructions
        self.config = config_manager
        self._setup_directories()
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
        logger = logging.getLogger(f"GroupProcessor_{self.group_version.pipeline_id}")
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = os.path.join(
            self.output_dir,
            "logs",
            f"group_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )

        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            logger.info(f"Logging initialized: {log_file}")
        except Exception as e:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.error(f"Failed to create file handler: {str(e)}")

        return logger

    def _setup_directories(self):
        if self.config.get("file_system", "local") == "local":
            directories = [
                self.output_dir,
                os.path.join(self.output_dir, "logs"),
                os.path.join(self.output_dir, "temp"),
            ]
            for directory in directories:
                os.makedirs(directory, exist_ok=True)

    def _analyze_groups(self, entities_data: Dict) -> Dict:
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
            return json.loads(response.content)

        except Exception as e:
            self.logger.error(f"Error in group analysis: {str(e)}")
            raise

    def process(self) -> ProcessingResult:
        try:
            self.logger.info(
                f"Starting group analysis for pipeline: {self.group_version.pipeline_id}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            # Load merged entities results
            merge_version = next(
                (
                    v
                    for v in self.group_version.merge_versions
                    if v.version_id == self.group_version.current_merge_id
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
            groups_path = os.path.join(self.output_dir, "output.json")
            with open(groups_path, "w", encoding="utf-8") as f:
                json.dump(groups_analysis, f, indent=2, ensure_ascii=False)

            return ProcessingResult(
                success=True,
                status="completed",
                message="Group analysis completed successfully",
            )

        except Exception as e:
            self.logger.error(f"Error during group analysis: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Group analysis failed: {str(e)}",
                error=str(e),
            )
