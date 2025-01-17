from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import os
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import concurrent.futures

from ..models.models import ParseVersion, ExtractVersion
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult


@dataclass
class Entity:
    name: str
    category: str
    definition: str
    characteristics: List[str]
    functions: List[str]
    attributes: List[str]
    constraints: List[str]
    related_concepts: List[str]


class ExtractProcessor(BaseProcessor):
    def __init__(
        self,
        parse_version: ParseVersion,
        extract_version: ExtractVersion,
        config_manager: ConfigManager,
    ):
        self.parse_version = parse_version
        self.extract_version = extract_version
        self.system_prompt = self.extract_version.system_prompt
        self.initial_entity_extraction_prompt = (
            self.extract_version.initial_entity_extraction_prompt
        )
        self.iterative_extract_entities_prompt = (
            self.extract_version.iterative_extract_entities_prompt
        )
        self.entity_details_prompt = self.extract_version.entity_details_prompt
        # TODO: Implement custom instructions
        self.custom_instructions = self.extract_version.custom_instructions
        super().__init__(config_manager)

    @property
    def _get_logger_name(self) -> str:
        """Return the logger name for this processor."""
        return f"ExtractProcessor_{self.extract_version.version_id}"

    @property
    def _get_output_dir(self) -> str:
        return self.extract_version.output_dir

    def _initial_extraction(self, content: str) -> tuple[List[str], List[Dict]]:
        """Perform initial extraction of entities and relationships."""
        self.logger.info("Performing initial entity extraction")

        try:
            prompt_content = [
                {"type": "text", "text": content},
                {"type": "text", "text": self.initial_entity_extraction_prompt},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )

            chain = prompt | self.model
            response = chain.invoke({})
            result = json.loads(response.content)

            self.logger.info(
                f"Initial extraction found {len(result['entities'])} entities and "
                f"{len(result['relationships'])} relationships"
            )
            return result["entities"], result["relationships"]

        except Exception as e:
            self.logger.error(f"Error in initial entity extraction: {str(e)}")
            raise

    def _iterative_extraction(
        self,
        content: str,
        previous_entities: List[str],
        previous_relationships: List[Dict],
    ) -> tuple[List[str], List[Dict]]:
        """Perform another iteration of entity and relationship extraction."""
        self.logger.info("Performing iterative extraction")

        try:
            formatted_relationships = "\n".join(
                f"- {rel['source']} {rel['type']} {rel['target']}: {rel['description']}"
                for rel in previous_relationships
            )

            prompt_content = [
                {"type": "text", "text": content},
                {
                    "type": "text",
                    "text": self.iterative_extract_entities_prompt.format(
                        previous_entities="\n".join(
                            f"- {entity}" for entity in previous_entities
                        ),
                        previous_relationships=formatted_relationships,
                    ),
                },
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )

            chain = prompt | self.model
            response = chain.invoke({})
            result = json.loads(response.content)

            return result.get("new_entities", []), result.get("new_relationships", [])

        except Exception as e:
            self.logger.error(f"Error in iterative extraction: {str(e)}")
            raise

    def _get_entity_details(self, entity: str, content: str) -> Entity:
        """Get detailed information about a specific entity."""
        self.logger.info(f"Getting details for entity: {entity}")

        try:
            prompt_content = [
                {"type": "text", "text": content},
                {
                    "type": "text",
                    "text": self.entity_details_prompt.format(entity=entity),
                },
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )

            chain = prompt | self.model
            response = chain.invoke({})
            result = json.loads(response.content)

            return Entity(**result)

        except Exception as e:
            self.logger.error(f"Error getting details for entity {entity}: {str(e)}")
            raise

    def process(self, iterations: Optional[int] = None) -> ProcessingResult:
        """Process all files in the pipeline and extract entities and relationships."""
        try:
            iterations = iterations or int(self.config.get("entity_max_iterations", 3))
            self.logger.info(
                f"Starting entity extraction for pipeline: {self.extract_version.pipeline_id}"
            )

            with open(self.parse_version.output_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Initial extraction
            all_entities, all_relationships = self._initial_extraction(content)
            relationship_keys = {
                (r["source"], r["target"], r["type"]) for r in all_relationships
            }

            # Iterative extractions
            for i in range(iterations - 1):
                self.logger.info(f"Starting iteration {i + 2} of {iterations}")
                new_entities, new_relationships = self._iterative_extraction(
                    content, all_entities, all_relationships
                )

                # Add new unique entities
                all_entities.extend([e for e in new_entities if e not in all_entities])

                # Add new unique relationships
                for rel in new_relationships:
                    rel_key = (rel["source"], rel["target"], rel["type"])
                    if rel_key not in relationship_keys:
                        relationship_keys.add(rel_key)
                        all_relationships.append(rel)

            # Get detailed information for each entity
            entity_details = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_entity = {
                    executor.submit(self._get_entity_details, entity, content): entity
                    for entity in all_entities
                }

                for future in concurrent.futures.as_completed(future_to_entity):
                    entity = future_to_entity[future]
                    try:
                        entity_info = future.result()
                        entity_details[entity] = entity_info.__dict__
                    except Exception as e:
                        self.logger.error(f"Error processing entity {entity}: {str(e)}")

            # Prepare final analysis
            extraction = {
                "entities": entity_details,
                "relationships": all_relationships,
            }

            # Save extraction to file
            extraction_path = os.path.join(self.output_dir, "output.json")
            with open(extraction_path, "w", encoding="utf-8") as f:
                json.dump(extraction, f, indent=2, ensure_ascii=False)

            self.logger.info("Entity extraction completed successfully")
            return ProcessingResult(
                success=True,
                status="completed",
                message="Entity extraction completed successfully",
                data=extraction,
                output_path=extraction_path,
            )

        except Exception as e:
            self.logger.error(
                f"Error during entity extraction: {str(e)}", exc_info=True
            )
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Entity extraction failed: {str(e)}",
                error=str(e),
            )
