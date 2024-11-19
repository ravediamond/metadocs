# src/processors/groups/processor.py

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
from ..prompts.group_prompts import SYSTEM_PROMPT, GROUP_ANALYSIS_PROMPT


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    groups_path: Optional[str] = None


class GroupProcessor:
    def __init__(self, file_model: FileModel):
        self.file_model = file_model
        self.logger = self._setup_logger()
        self.output_dir = os.path.join(
            settings.PROCESSING_DIR,
            str(self.file_model.domain_id),
            str(self.file_model.file_id),
            "groups_analysis",
        )
        self.model = self._setup_model()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"GroupProcessor_{self.file_model.file_id}")
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

    def _setup_model(self) -> ChatBedrock:
        return ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="us-east-1",
            model_kwargs=dict(temperature=0, max_tokens=4096),
        )

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
                f"Starting group analysis for file: {self.file_model.filename}"
            )
            os.makedirs(self.output_dir, exist_ok=True)

            # Load entity analysis results
            with open(
                self.file_model.entity_extraction_path, "r", encoding="utf-8"
            ) as f:
                entities_data = json.load(f)

            # Analyze groups
            groups_analysis = self._analyze_groups(entities_data)

            # Save analysis results
            groups_path = os.path.join(self.output_dir, "groups_analysis.json")
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
