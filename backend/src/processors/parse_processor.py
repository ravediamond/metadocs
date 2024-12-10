import fitz
from PIL import Image
import base64
from io import BytesIO
import os
from dataclasses import dataclass
from typing import List, Dict
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.models import (
    ParseVersion,
    FileVersion,
)
from ..llm.llm_factory import LLMConfig, LLMFactory
from ..core.config import FILE_SYSTEM, ConfigManager


# TODO: Implement quality score and improvement message
@dataclass
class ProcessingResult:
    success: bool
    status: str
    message: str
    error: str


class ParseProcessor:
    def __init__(
        self,
        file_version: FileVersion,
        parse_version: ParseVersion,
        config_manager: ConfigManager,
    ):
        self.file_version = file_version
        self.parse_version = parse_version
        self.system_prompt = self.parse_version.system_prompt
        self.readability_prompt = self.parse_version.readability_prompt
        self.convert_prompt = self.parse_version.convert_prompt
        # TODO: Implement custom instructions
        self.custom_instructions = self.parse_version.custom_instructions
        self.config = config_manager
        self._setup_directories()
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
        """Setup logging for the processor with proper directory handling."""
        logger = logging.getLogger(
            f"ParseProcessor_{self.file_version.file_version_id}"
        )
        logger.setLevel(logging.DEBUG)

        # Remove any existing handlers to avoid duplicate logging
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create logs directory path
        logs_dir = os.path.join(self.parse_version.output_dir, "logs")

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"parse_processor_{timestamp}.log")

        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # Add a stream handler for console output
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            logger.info(f"Logging initialized. Log file: {log_file}")
        except Exception as e:
            # Fallback to console-only logging if file handler fails
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.error(
                f"Failed to create file handler: {str(e)}. Falling back to console logging only."
            )

        return logger

    def _setup_directories(self):
        """Create all necessary directories for processing and logging."""
        if self.config.get("file_system", "local") == "local":
            # Create base output directory
            os.makedirs(self.parse_version.output_dir, exist_ok=True)

            # Create subdirectories
            directories = [
                os.path.join(self.parse_version.output_dir, "images"),
                os.path.join(self.parse_version.output_dir, "logs"),
                os.path.join(self.parse_version.output_dir, "temp"),
            ]

            for directory in directories:
                os.makedirs(directory, exist_ok=True)

    def _convert_page_to_image(self, page: fitz.Page) -> Image.Image:
        """Convert PDF page to PIL Image."""
        self.logger.debug(f"Converting page {page.number + 1} to image")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.logger.debug(f"Page {page.number + 1} converted successfully")
        return img

    def _encode_image(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG", quality=95)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _save_image(self, image: Image.Image, page_num: int):
        """Save the image to the output directory."""
        image_path = os.path.join(
            self.parse_version.output_dir, "images", f"page_{page_num + 1}.png"
        )
        image.save(image_path, "PNG", quality=95)
        return image_path

    def _check_quality(self, images: List[Image.Image]) -> Dict:
        """Check image quality using LLM."""
        self.logger.info("Checking document quality")
        content = []
        for idx, img in enumerate(images, 1):
            self.logger.debug(f"Processing quality check for image {idx}")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{self._encode_image(img)}"
                    },
                }
            )
        content.append({"type": "text", "text": self.readability_prompt})

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=self.system_prompt), HumanMessage(content=content)]
        )

        chain = prompt | self.model
        response = chain.invoke({})
        result = json.loads(response.content)
        self.logger.info(f"Quality check result: {result}")
        return result

    def _process_page(self, page_num: int, image: Image.Image) -> Dict[str, str]:
        """Process a single page and return markdown content."""
        self.logger.info(f"Processing page {page_num + 1}")

        # Save the image
        image_path = self._save_image(image, page_num)

        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{self._encode_image(image)}"
                },
            },
            {
                "type": "text",
                "text": self.convert_prompt,
            },  # Using the base_prompt passed in constructor
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=self.system_prompt), HumanMessage(content=content)]
        )

        chain = prompt | self.model
        response = chain.invoke({})
        markdown = response.content

        # Save individual page markdown
        page_path = os.path.join(
            self.parse_version.output_dir, f"page_{page_num + 1}.md"
        )
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        return {
            "markdown": markdown,
            "image_path": image_path,
            "markdown_path": page_path,
        }

    def process(self) -> ProcessingResult:
        """Process the PDF file and return results."""
        try:
            batch_size = int(self.config.get("processing_batch_size", 5))
            self.logger.info(
                f"Starting processing for file: {self.file_version.file_id}"
            )

            # Open PDF
            doc = fitz.open(self.file_version.filepath)
            self.logger.info(f"PDF opened successfully. Total pages: {len(doc)}")

            # Check quality of first few pages
            first_pages = [
                self._convert_page_to_image(doc[i]) for i in range(min(5, len(doc)))
            ]
            quality_result = self._check_quality(first_pages)

            if quality_result["confidence"] < 75:
                self.parse_version.status = "failed"
                self.parse_version.error = (
                    f"Quality check failed: {quality_result['problem']}"
                )
                self.logger.warning(
                    f"Quality check failed: {quality_result['problem']}"
                )
                return ProcessingResult(
                    success=False,
                    message=f"Quality check failed: {quality_result['problem']}",
                    quality_score=quality_result["confidence"],
                )

            # Process pages in parallel
            all_results = []
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                future_to_page = {
                    executor.submit(
                        self._process_page,
                        page_num,
                        self._convert_page_to_image(doc[page_num]),
                    ): page_num
                    for page_num in range(len(doc))
                }

                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        result = future.result()
                        all_results.append((page_num, result))
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {str(e)}")
                        raise

            # Sort results by page number and combine markdown
            all_results.sort(key=lambda x: x[0])
            combined_path = os.path.join(self.parse_version.output_dir, "output.md")
            with open(combined_path, "w", encoding="utf-8") as f:
                f.write(
                    "\n\n---\n\n".join(result["markdown"] for _, result in all_results)
                )

            self.logger.info("Processing completed successfully")
            return ProcessingResult(
                success=True,
                status="completed",
                message="PDF processed successfully",
            )

        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                status="failed",
                message=f"Processing failed: {str(e)}",
                error=str(e),
            )
