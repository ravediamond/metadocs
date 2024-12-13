import fitz
from PIL import Image
import base64
from io import BytesIO
import os
from typing import List, Dict
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from ..models.models import (
    ParseVersion,
    FileVersion,
)
from ..core.config import ConfigManager
from .base_processor import BaseProcessor, ProcessingResult


class ParseProcessor(BaseProcessor):
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
        super().__init__(config_manager)

    def _get_output_dir(self) -> str:
        return self.parse_version.output_dir

    def _get_logger_name(self) -> str:
        return f"ParseProcessor_{self.file_version.file_version_id}"

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
