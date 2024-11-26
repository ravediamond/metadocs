from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import concurrent.futures

from ...models.models import ProcessingPipeline
from ..prompts.entity_prompts import (
    SYSTEM_PROMPT,
    INITIAL_ENTITY_EXTRACTION_PROMPT,
    ITERATIVE_ENTITY_EXTRACTION_PROMPT,
    ENTITY_DETAILS_PROMPT,
)
from ...llm.llm_factory import LLMConfig, LLMFactory


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


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    analysis_path: Optional[str] = None


class EntityProcessor:
    def __init__(self, pipeline: ProcessingPipeline, config_manager):
        """Initialize with pipeline instead of single file"""
        self.pipeline = pipeline
        self.config = config_manager
        self.output_dir = os.path.join(
            self.config.get("processing_dir", "processing_output"),
            str(self.pipeline.domain_id),
            "entity_extraction",
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
        """Setup logging for the processor."""
        logger = logging.getLogger(f"EntityProcessor_{self.pipeline.pipeline_id}")
        logger.setLevel(logging.DEBUG)

        os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)

        file_handler = logging.FileHandler(
            os.path.join(
                self.output_dir,
                "logs",
                f"entity_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            )
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def _initial_extraction(self, content: str) -> tuple[List[str], List[Dict]]:
        """Perform initial extraction of entities and relationships."""
        self.logger.info("Performing initial entity extraction")

        try:
            prompt_content = [
                {"type": "text", "text": content},
                {"type": "text", "text": INITIAL_ENTITY_EXTRACTION_PROMPT},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
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
                    "text": ITERATIVE_ENTITY_EXTRACTION_PROMPT.format(
                        previous_entities="\n".join(
                            f"- {entity}" for entity in previous_entities
                        ),
                        previous_relationships=formatted_relationships,
                    ),
                },
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
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
                {"type": "text", "text": ENTITY_DETAILS_PROMPT.format(entity=entity)},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
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
                f"Starting entity extraction for pipeline: {self.pipeline.pipeline_id}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            all_content = []
            file_metadata = []

            pipeline_files = self.pipeline.files

            if not pipeline_files:
                return ProcessingResult(
                    success=False, message="No files found for processing"
                )

            # Process each file in the pipeline
            for file in pipeline_files:
                try:
                    with open(file.markdown_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        all_content.append(content)
                        file_metadata.append(
                            {"file_id": str(file.file_id), "filename": file.filename}
                        )
                except Exception as e:
                    self.logger.error(f"Error reading file {file.filename}: {str(e)}")
                    continue

            if not all_content:
                return ProcessingResult(
                    success=False,
                    message="No files could be processed",
                )

            # Combine all content with clear separators
            combined_content = "\n\n---\n\n".join(all_content)

            # Initial extraction
            all_entities, all_relationships = self._initial_extraction(combined_content)
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
                "metadata": {
                    "pipeline_id": str(self.pipeline.pipeline_id),
                    "domain_id": str(self.pipeline.domain_id),
                    "processed_files": file_metadata,
                    "iterations": iterations,
                    "total_entities_attempted": len(all_entities),
                    "total_entities_processed": len(entity_details),
                    "total_unique_relationships": len(relationship_keys),
                    "analysis_timestamp": datetime.now().isoformat(),
                    "failed_entities": [
                        e for e in all_entities if e not in entity_details
                    ],
                },
            }

            # Save extraction to file
            extraction_path = os.path.join(self.output_dir, "entity_extraction.json")
            with open(extraction_path, "w", encoding="utf-8") as f:
                json.dump(extraction, f, indent=2, ensure_ascii=False)

            self.logger.info("Entity extraction completed successfully")
            return ProcessingResult(
                success=True,
                message="Entity extraction completed successfully",
                data=extraction,
                analysis_path=extraction_path,
            )

        except Exception as e:
            self.logger.error(
                f"Error during entity extraction: {str(e)}", exc_info=True
            )
            return ProcessingResult(
                success=False, message=f"Entity extraction failed: {str(e)}"
            )
