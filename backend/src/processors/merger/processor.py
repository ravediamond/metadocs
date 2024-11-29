from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import os
import logging
from datetime import datetime
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from ...models.models import ProcessingPipeline
from ...llm.llm_factory import LLMConfig, LLMFactory
from ...core.config import ConfigManager


@dataclass
class MergeResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    merged_path: Optional[str] = None


class MergeProcessor:
    def __init__(self, pipeline: ProcessingPipeline, config: ConfigManager):
        self.pipeline = pipeline
        self.domain_id = pipeline.domain_id
        self.file_models = [
            file for file in pipeline.files if file.processing_status == "completed"
        ]
        self.config = config
        self.output_dir = os.path.join(
            self.config.get("processing_dir", "processing_output"),
            str(self.domain_id),
            "merged",
        )
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
        logger = logging.getLogger(f"EntityMergerProcessor_{self.domain_id}")
        logger.setLevel(logging.DEBUG)

        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(
            os.path.join(
                log_dir,
                f"entity_merger_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            )
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        return logger

    def _merge_batch(self, entities_batch: List[Dict]) -> Dict:
        content = [
            {"type": "text", "text": json.dumps(entities_batch)},
            {"type": "text", "text": ENTITY_MERGE_PROMPT},
        ]
        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
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
            {"type": "text", "text": ENTITY_DETAILS_PROMPT},
        ]
        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )
        chain = prompt | self.model
        response = chain.invoke({})
        return json.loads(response.content)

    def process(self) -> MergeResult:
        try:
            self.logger.info(f"Starting entity merging for domain {self.domain_id}")
            os.makedirs(self.output_dir, exist_ok=True)

            if len(self.file_models) == 1:
                self.logger.info(
                    "Single file detected, returning entities without merging"
                )
                with open(self.file_models[0].entity_extraction_path, "r") as f:
                    entities_data = json.load(f)
                    # Check if 'entities' key exists and get its value, otherwise use the whole data
                    entities_to_return = entities_data.get("entities", entities_data)

                merged_path = os.path.join(self.output_dir, "merged_entities.json")
                with open(merged_path, "w") as f:
                    json.dump({"entities": entities_to_return}, f, indent=2)

                return MergeResult(
                    success=True,
                    message="Single file processed without merging",
                    data={"entities": entities_to_return},
                    merged_path=merged_path,
                )

            # Collect all entities
            all_entities = {}
            for file in self.file_models:
                with open(file.entity_extraction_path, "r") as f:
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

            merged_path = os.path.join(self.output_dir, "merged_entities.json")
            with open(merged_path, "w") as f:
                json.dump(final_entities, f, indent=2)

            return MergeResult(
                success=True,
                message="Entity merging completed",
                data=final_entities,
                merged_path=merged_path,
            )

        except Exception as e:
            self.logger.error(f"Error during entity merging: {str(e)}", exc_info=True)
            return MergeResult(
                success=False, message=f"Entity merging failed: {str(e)}"
            )
