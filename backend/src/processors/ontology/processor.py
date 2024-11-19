from dataclasses import dataclass
from typing import Dict, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ...models.models import File as FileModel
from ...core.config import settings
from ..prompts.ontology_prompts import SYSTEM_PROMPT, MERMAID_GENERATION_PROMPT


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    diagram_path: Optional[str] = None


class OntologyProcessor:
    def __init__(self, file_model: FileModel):
        self.file_model = file_model
        self.logger = self._setup_logger()
        self.output_dir = os.path.join(
            settings.PROCESSING_DIR,
            str(self.file_model.domain_id),
            str(self.file_model.file_id),
            "ontology",
        )
        self.model = self._setup_model()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"OntologyProcessor_{self.file_model.file_id}")
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

    def _setup_model(self) -> ChatBedrock:
        return ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="us-east-1",
            model_kwargs=dict(temperature=0, max_tokens=4096),
        )

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
                f"Starting ontology generation for file: {self.file_model.filename}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            with open(
                self.file_model.entity_extraction_path, "r", encoding="utf-8"
            ) as f:
                entities_data = json.load(f)

            with open(self.file_model.entity_grouping_path, "r", encoding="utf-8") as f:
                groups_data = json.load(f)

            mermaid_diagram = self._generate_mermaid(entities_data, groups_data)

            diagram_path = os.path.join(self.output_dir, "ontology.md")
            with open(diagram_path, "w", encoding="utf-8") as f:
                f.write(mermaid_diagram)

            return ProcessingResult(
                success=True,
                message="Ontology diagram generated successfully",
                data={"mermaid": mermaid_diagram},
                diagram_path=diagram_path,
            )

        except Exception as e:
            self.logger.error(f"Error generating ontology: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False, message=f"Ontology generation failed: {str(e)}"
            )
