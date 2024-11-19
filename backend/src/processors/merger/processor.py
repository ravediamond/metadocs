from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from ...models.models import File as FileModel
from ...core.config import settings
from ..prompts.merger_prompts import (
    SYSTEM_PROMPT,
    ENTITY_MERGE_PROMPT,
    ENTITY_DETAILS_PROMPT,
)
from ...llm.llm_factory import LLMConfig, LLMFactory


@dataclass
class MergeResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    merged_path: Optional[str] = None


class EntityMerger:
    def __init__(self, domain_id: str, file_models: List[FileModel]):
        self.domain_id = domain_id
        self.file_models = file_models
        self.logger = self._setup_logger()
        self.output_dir = os.path.join(
            settings.PROCESSING_DIR, str(domain_id), "merged"
        )
        self.llm_config = self._setup_llm_config()
        self.model = self._setup_model()

    def _setup_llm_config(self) -> LLMConfig:
        """Initialize the LLM config"""
        return LLMConfig(
            provider="bedrock",
            profile_name="my-aws-profile",
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            model_kwargs={"temperature": 0, "max_tokens": 4096},
        )

    def _setup_model(self) -> ChatBedrock:
        """Initialize the LLM model"""
        return LLMFactory(self.llm_config).create_model()

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
