from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import os
import logging
from datetime import datetime
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from ..models.models import ExtractVersion, MergeVersion
from ..llm.llm_factory import LLMConfig, LLMFactory
from ..core.config import FILE_SYSTEM, ConfigManager


@dataclass
class ProcessingResult:
    success: bool
    status: str
    message: str
    error: str


class MergeProcessor:
    def __init__(
        self,
        extract_versions: List[ExtractVersion],
        merge_version: MergeVersion,
        config_manager: ConfigManager,
    ):
        self.extract_versions = extract_versions
        self.merge_version = merge_version
        self.system_prompt = self.merge_version.system_prompt
        self.entity_details_prompt = self.merge_version.entity_details_prompt
        self.entity_merge_prompt = self.merge_version.entity_merge_prompt
        # TODO: Implement custom instructions
        self.custom_instructions = self.merge_version.custom_instructions
        self.config = config_manager
        self._setup_directories()
        self.logger = self._setup_logger()
        self.model = self._setup_model()

    def _setup_model(self) -> ChatBedrock:
        """Initialize the LLM model based on domain configuration"""
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
        logger = logging.getLogger(f"MergeProcessor_{self.merge_version.pipeline_id}")
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = os.path.join(
            self.output_dir,
            "logs",
            f"merge_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
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

    def _merge_batch(self, entities_batch: List[Dict]) -> Dict:
        content = [
            {"type": "text", "text": json.dumps(entities_batch)},
            {"type": "text", "text": self.entity_merge_prompt},
        ]
        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=self.system_prompt), HumanMessage(content=content)]
        )
        chain = prompt | self.model
        response = chain.invoke({})
        return json.loads(response.content)

    def _process_merged_entities(
        self, merged_ids: List[str], all_entities: Dict
    ) -> Dict:
        content = [
            {
                "type": "text",
                "text": json.dumps(
                    {"merged_ids": merged_ids, "entities": all_entities}
                ),
            },
            {"type": "text", "text": self.entity_details_prompt},
        ]
        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=self.system_prompt), HumanMessage(content=content)]
        )
        chain = prompt | self.model
        response = chain.invoke({})
        return json.loads(response.content)

    def process(self) -> ProcessingResult:
        try:
            self.logger.info(f"Starting entity merging for domain {self.domain_id}")
            os.makedirs(self.output_dir, exist_ok=True)

            if len(self.extract_versions) == 1:
                self.logger.info(
                    "Single file detected, returning entities without merging"
                )
                with open(self.extract_versions[0].output_path, "r") as f:
                    entities_data = json.load(f)
                    # Check if 'entities' key exists and get its value, otherwise use the whole data
                    entities_to_return = entities_data.get("entities", entities_data)

                merged_path = os.path.join(self.output_dir, "output.json")
                with open(merged_path, "w") as f:
                    json.dump({"entities": entities_to_return}, f, indent=2)

                return ProcessingResult(
                    success=True,
                    status="completed",
                    message="Single file processed without merging",
                )

            # Collect all entities
            all_entities = {}
            for extract in self.extract_versions:
                with open(extract.output_path, "r") as f:
                    data = json.load(f)
                    all_entities.update(data.get("entities", {}))

            # Process in batches
            entity_batches = [
                list(all_entities.items())[i : i + 10]
                for i in range(0, len(all_entities), 10)
            ]
            merged_entity_ids = []

            for batch in entity_batches:
                merge_result = self._merge_batch(dict(batch))
                merged_entity_ids.extend(merge_result.get("merged_entity_ids", []))

            # Process merged entities
            final_entities = self._process_merged_entities(
                merged_entity_ids, all_entities
            )

            merged_path = os.path.join(self.output_dir, "output.json")
            with open(merged_path, "w") as f:
                json.dump(final_entities, f, indent=2)

            return ProcessingResult(
                success=True,
                status="completed",
                message="Entity merging completed",
            )

        except Exception as e:
            self.logger.error(f"Error during entity merging: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Entity merging failed: {str(e)}",
                error=str(e),
            )
