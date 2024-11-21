from dataclasses import dataclass
from typing import Dict, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ...models.models import DomainProcessing
from ..prompts.ontology_prompts import SYSTEM_PROMPT, MERMAID_GENERATION_PROMPT
from ...llm.llm_factory import LLMConfig, LLMFactory


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    diagram_path: Optional[str] = None


class OntologyProcessor:
    def __init__(self, domain_processing: DomainProcessing, config_manager):
        self.domain_processing = domain_processing
        self.config = config_manager
        self.output_dir = os.path.join(
            self.config.get("processing_dir", "processing_output"),
            str(self.domain_processing.domain_id),
            "ontology",
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
        logger = logging.getLogger(
            f"OntologyProcessor_{self.domain_processing.processing_id}"
        )
        logger.setLevel(logging.DEBUG)
        os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)

        file_handler = logging.FileHandler(
            os.path.join(
                self.output_dir,
                "logs",
                f"ontology_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            )
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        return logger

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
                {"type": "text", "text": MERMAID_GENERATION_PROMPT},
            ]

            prompt = ChatPromptTemplate.from_messages(
                [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
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
                f"Starting ontology generation for domain processing: {self.domain_processing.processing_id}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            with open(
                self.domain_processing.merged_entities_path, "r", encoding="utf-8"
            ) as f:
                entities_data = json.load(f)

            with open(
                self.domain_processing.entity_grouping_path, "r", encoding="utf-8"
            ) as f:
                groups_data = json.load(f)

            mermaid_diagram = self._generate_mermaid(entities_data, groups_data)

            diagram_path = os.path.join(self.output_dir, "ontology.md")
            with open(diagram_path, "w", encoding="utf-8") as f:
                f.write(mermaid_diagram)

            self.domain_processing.ontology_path = diagram_path
            self.domain_processing.status = "completed"
            self.domain_processing.completed_at = datetime.now()

            return ProcessingResult(
                success=True,
                message="Ontology diagram generated successfully",
                data={"mermaid": mermaid_diagram},
                diagram_path=diagram_path,
            )

        except Exception as e:
            self.logger.error(f"Error generating ontology: {str(e)}", exc_info=True)
            self.domain_processing.status = "failed"
            self.domain_processing.error = str(e)
            return ProcessingResult(
                success=False, message=f"Ontology generation failed: {str(e)}"
            )
