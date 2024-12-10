from typing import List, Dict
import json
import os
import logging
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from ..models.models import ExtractVersion, MergeVersion
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult


class MergeProcessor(BaseProcessor):
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
        super().__init__(config_manager)

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
