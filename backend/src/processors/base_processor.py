from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime
import os
from langchain_aws.chat_models import ChatBedrock
from ..core.config import ConfigManager
from ..llm.llm_factory import LLMConfig, LLMFactory


# TODO: Implement quality score and improvement message
@dataclass
class ProcessingResult:
    success: bool
    status: str
    message: str
    error: str = ""
    data: Dict = None
    output_path: str = ""


class BaseProcessor(ABC):
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.output_dir = self._get_output_dir
        self._setup_directories()
        self.logger = self._setup_logger()
        self.model = self._setup_model()

    @property
    @abstractmethod
    def _get_output_dir(self) -> str:
        """Abstract property for getting output directory path."""
        pass

    @property
    @abstractmethod
    def _get_logger_name(self) -> str:
        """Abstract property for getting logger name."""
        pass

    def _setup_directories(self):
        if self.config.get("file_system", "local") == "local":
            directories = [
                self.output_dir,
                os.path.join(self.output_dir, "logs"),
                os.path.join(self.output_dir, "temp"),
                os.path.join(self.output_dir, "images"),
            ]
            for directory in directories:
                os.makedirs(directory, exist_ok=True)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(self._get_logger_name)
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = os.path.join(
            self.output_dir,
            "logs",
            f"{self.__class__.__name__.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
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

    def _setup_model(self) -> ChatBedrock:
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

    @abstractmethod
    def process(self) -> ProcessingResult:
        pass
