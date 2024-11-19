import fitz
from PIL import Image
import base64
from io import BytesIO
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ...models.models import File as FileModel
from ...core.config import settings
from ..prompts.document_prompts import (
    SYSTEM_PROMPT,
    CHECK_READABILITY_PROMPT,
    CONVERT_TO_MARKDOWN_PROMPT,
)
from ...llm.llm_factory import LLMConfig, LLMFactory


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Optional[Dict] = None
    markdown_path: Optional[str] = None


class PDFProcessor:
    def __init__(self, file_model: FileModel):
        self.file_model = file_model
        self.output_dir = os.path.join(
            settings.PROCESSING_DIR,
            str(self.file_model.domain_id),
            str(self.file_model.file_id),
        )
        self.logger = self._setup_logger()
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

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the processor."""
        logger = logging.getLogger(f"PDFProcessor_{self.file_model.file_id}")
        logger.setLevel(logging.DEBUG)

        # Create logs directory
        logs_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            os.path.join(logs_dir, f"processor_{timestamp}.log")
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def _setup_directories(self):
        """Create necessary directories for processing."""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "images"), exist_ok=True)

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
        image_path = os.path.join(self.output_dir, "images", f"page_{page_num + 1}.png")
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
        content.append({"type": "text", "text": CHECK_READABILITY_PROMPT})

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
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
            {"type": "text", "text": CONVERT_TO_MARKDOWN_PROMPT},
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )

        chain = prompt | self.model
        response = chain.invoke({})
        markdown = response.content

        # Save individual page markdown
        page_path = os.path.join(self.output_dir, f"page_{page_num + 1}.md")
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        return {
            "markdown": markdown,
            "image_path": image_path,
            "markdown_path": page_path,
        }

    def process(self, batch_size: int = 5) -> ProcessingResult:
        """Process the PDF file and return results."""
        try:
            self.logger.info(
                f"Starting processing for file: {self.file_model.filename}"
            )
            self._setup_directories()

            # Open PDF
            doc = fitz.open(self.file_model.filepath)
            self.logger.info(f"PDF opened successfully. Total pages: {len(doc)}")

            # Check quality of first few pages
            first_pages = [
                self._convert_page_to_image(doc[i]) for i in range(min(5, len(doc)))
            ]
            quality_result = self._check_quality(first_pages)

            if quality_result["confidence"] < 75:
                self.logger.warning(
                    f"Quality check failed: {quality_result['problem']}"
                )
                return ProcessingResult(
                    success=False,
                    message=f"Quality check failed: {quality_result['problem']}",
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
            combined_path = os.path.join(self.output_dir, "combined.md")
            with open(combined_path, "w", encoding="utf-8") as f:
                f.write(
                    "\n\n---\n\n".join(result["markdown"] for _, result in all_results)
                )

            self.logger.info("Processing completed successfully")
            return ProcessingResult(
                success=True,
                message="PDF processed successfully",
                data={
                    "total_pages": len(doc),
                    "output_dir": self.output_dir,
                    "page_results": [
                        {
                            "page_num": page_num + 1,
                            "image_path": result["image_path"],
                            "markdown_path": result["markdown_path"],
                        }
                        for page_num, result in all_results
                    ],
                },
                markdown_path=combined_path,
            )

        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False, message=f"Processing failed: {str(e)}"
            )
