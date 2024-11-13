import fitz
from PIL import Image
import base64
from io import BytesIO
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import json
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import re
import logging
from datetime import datetime
import sys
import concurrent.futures
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

SYSTEM_PROMPT = """You are an advanced vision-capable assistant specialized in analyzing and transforming visual content.
"""

CHECK_READABILITY_PROMPT = """
Analyze this image and provide a detailed readability assessment with specific scores.
For Text-Background Contrast (25 points), rate the contrast ratio and note any contrast issues.
For Text Quality (25 points), assess the estimated DPI, character clarity (High/Medium/Low), and any quality issues.
For Layout Structure (25 points), evaluate margin consistency (10 points) and organization clarity (15 points), noting any layout problems.
For Text Completeness (25 points), score text visibility (15 points) and integrity (10 points), identifying any missing or truncated content.
Provide a confidence Score out of 100. If total score is below 70, list the description of the problem. 

Provide your responseas a valid JSON object with:
1. A confidence score (0-100) as a number (not a string)
2. A problem description as a string

Your response should be in this exact format, with no extra formatting or line breaks:
{"confidence": 80, "problem": "Description of the readability issues"}

Example of valid output:
{"confidence": 75, "problem": "Text size varies significantly with some sections being too small for comfortable mobile viewing"}
"""

CONVERT_TO_MARKDOWN_PROMPT = """Convert the image content to properly formatted markdown, following these rules:

1. Document Structure:
  - Start with the main title using a single #
  - Only use table format for actual tabular data 
  - Use section headings (##, ###) for distinct content sections
  - Add horizontal rules (---) between major sections only when there's a clear visual break

2. Table Formatting:
  - Always include proper header row and alignment separators
  - Use consistent column alignment with colons:
    Left align: |:---|
    Center align: |:---:|
    Right align: |---:|
  - For cells with multiple lines, use <br> for line breaks
  - Keep related information together in the same cell
  - For lists within table cells, maintain proper formatting with line breaks
  - Preserve any bold (**text**) or italic (*text*) formatting within cells

3. Lists and Content:
  - Use appropriate list markers:
    - Unordered lists: Use - consistently
    - Ordered lists: Use 1., 2., etc.
  - Maintain list hierarchy with proper indentation (2 spaces)
  - Preserve original text emphasis (bold, italic)
  - Keep related content grouped together

4. Special Elements:
  - For headers spanning multiple columns, use proper markdown table syntax
  - Include any notes or special instructions as blockquotes using >
  - Format code or technical content with appropriate code blocks
  - Preserve any system-specific formatting or nomenclature
"""

BATCH_SIZE = 20  # Number of pages to process in parallel


@dataclass
class ImageQualityResult:
    confidence: float
    problem: str


@dataclass
class PageResult:
    page_num: int
    markdown: str
    image_path: str


@dataclass
class ProcessingResult:
    success: bool
    message: str
    data: Dict = None


def setup_logging(output_dir: str) -> logging.Logger:
    """Setup logging configuration."""
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    logger = logging.getLogger("PDFParser")
    logger.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, f"pdf_parser_{timestamp}.log")
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def convert_pdf_page_to_image(page: fitz.Page, logger: logging.Logger) -> Image.Image:
    """Convert a PDF page to PIL Image."""
    logger.debug(f"Converting page {page.number + 1} to image")
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        logger.debug(
            f"Successfully converted page {page.number + 1} to image of size {img.size}"
        )
        return img
    except Exception as e:
        logger.error(f"Error converting page {page.number + 1} to image: {str(e)}")
        raise


def encode_image_to_base64(image: Image.Image, logger: logging.Logger) -> str:
    """Convert PIL Image to base64 string."""
    logger.debug(f"Converting image of size {image.size} to base64")
    try:
        buffered = BytesIO()
        image.save(buffered, format="PNG", quality=95)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        logger.debug("Successfully converted image to base64")
        return encoded
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        raise


def save_image(image: Image.Image, filepath: str, logger: logging.Logger):
    """Save PIL Image to file."""
    logger.debug(f"Saving image to {filepath}")
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        image.save(filepath, "PNG", quality=95)
        logger.debug(f"Successfully saved image to {filepath}")
    except Exception as e:
        logger.error(f"Error saving image to {filepath}: {str(e)}")
        raise


def check_image_quality(
    model: ChatBedrock, images: List[Image.Image], logger: logging.Logger
) -> ImageQualityResult:
    """Check if images are readable using LLM."""
    logger.info(f"Checking quality of {len(images)} images")

    try:
        content = []
        for i, img in enumerate(images, 1):
            logger.debug(f"Processing image {i} for quality check")
            img_b64 = encode_image_to_base64(img, logger)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            )

        content.append({"type": "text", "text": CHECK_READABILITY_PROMPT})

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )

        logger.info("Sending request to LLM for quality check")
        chain = prompt | model
        response = chain.invoke({})
        result = json.loads(response.content)

        logger.info(
            f"Quality check results - Confidence: {result['confidence']}, Problem: {result['problem']}"
        )
        return ImageQualityResult(
            confidence=float(result["confidence"]),
            problem=result["problem"],
        )
    except Exception as e:
        logger.error(f"Error during image quality check: {str(e)}")
        raise


def process_single_page(
    model: ChatBedrock,
    page_num: int,
    image: Image.Image,
    images_dir: str,
    logger: logging.Logger,
) -> PageResult:
    """Process a single page and return its results."""
    logger.info(f"Processing page {page_num + 1}")

    try:
        # Save image
        image_filename = f"page_{page_num + 1}.png"
        image_path = os.path.join(images_dir, image_filename)
        save_image(image, image_path, logger)

        # Parse content
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encode_image_to_base64(image, logger)}"
                },
            },
            {"type": "text", "text": CONVERT_TO_MARKDOWN_PROMPT},
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )

        chain = prompt | model
        response = chain.invoke({})
        markdown = response.content

        return PageResult(
            page_num=page_num,
            markdown=markdown,
            image_path=image_path,
        )
    except Exception as e:
        logger.error(f"Error processing page {page_num + 1}: {str(e)}")
        raise


def process_batch(
    model: ChatBedrock,
    doc: fitz.Document,
    start_idx: int,
    end_idx: int,
    images_dir: str,
    logger: logging.Logger,
) -> List[PageResult]:
    """Process a batch of pages in parallel."""
    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        futures = []
        for page_num in range(start_idx, min(end_idx, len(doc))):
            image = convert_pdf_page_to_image(doc[page_num], logger)
            future = executor.submit(
                process_single_page,
                model,
                page_num,
                image,
                images_dir,
                logger,
            )
            futures.append(future)

        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error in batch processing: {str(e)}")
                raise

        return sorted(results, key=lambda x: x.page_num)


def process_pdf(pdf_path: str, output_dir: str = "output") -> ProcessingResult:
    """Process PDF file and generate enhanced markdown content."""
    logger = setup_logging(output_dir)
    logger.info(f"Starting PDF processing for {pdf_path}")
    logger.info(f"Output directory: {output_dir}")

    try:
        # Initialize model
        logger.info("Initializing Bedrock model")
        model = ChatBedrock(
            model_id="us.anthropic.claude-3-sonnet-20240229-v1:0",
            region_name="us-east-1",
            model_kwargs=dict(temperature=0, max_tokens=4096),
        )

        # Create output directories
        logger.debug("Creating output directories")
        os.makedirs(output_dir, exist_ok=True)
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        # Open PDF
        logger.info("Opening PDF file")
        doc = fitz.open(pdf_path)
        logger.info(f"PDF opened successfully. Total pages: {len(doc)}")

        # Check first 5 pages quality
        logger.info("Checking quality of first 5 pages")
        first_pages = [
            convert_pdf_page_to_image(doc[i], logger) for i in range(min(5, len(doc)))
        ]
        quality_result = check_image_quality(model, first_pages, logger)

        if quality_result.confidence < 75:
            logger.warning(
                f"Quality check failed. Confidence: {quality_result.confidence}"
            )
            return ProcessingResult(
                success=False,
                message=f"Image quality check failed. Confidence: {quality_result.confidence}. Problem: {quality_result.problem}",
            )

        # Process pages in batches
        logger.info("Beginning batch processing of pages")
        all_results = []
        for batch_start in range(0, len(doc), BATCH_SIZE):
            batch_end = batch_start + BATCH_SIZE
            logger.info(
                f"Processing batch: pages {batch_start + 1} to {min(batch_end, len(doc))}"
            )

            batch_results = process_batch(
                model,
                doc,
                batch_start,
                batch_end,
                images_dir,
                logger,
            )
            all_results.extend(batch_results)

        # Sort results by page number
        all_results.sort(key=lambda x: x.page_num)

        # Save individual markdown files and collect all markdown
        all_markdown = []
        for result in all_results:
            markdown_path = os.path.join(output_dir, f"page_{result.page_num + 1}.md")
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            all_markdown.append(result.markdown)

        # Save combined markdown
        logger.info("Saving combined markdown file")
        combined_path = os.path.join(output_dir, "combined.md")
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(all_markdown))

        logger.info("PDF processing completed successfully")
        return ProcessingResult(
            success=True,
            message="PDF processed successfully",
            data={
                "total_pages": len(doc),
                "output_dir": output_dir,
                "has_diagrams": any("@@@@@@" in md for md in all_markdown),
            },
        )

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        return ProcessingResult(
            success=False, message=f"Error processing PDF: {str(e)}"
        )
    finally:
        logger.info("Closing logging handlers")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process PDF and generate enhanced markdown content"
    )
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process")
    parser.add_argument(
        "--output", type=str, default="output", help="Output directory path"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Number of pages to process in parallel",
    )

    args = parser.parse_args()
    BATCH_SIZE = args.batch_size
    result = process_pdf(args.pdf_path, args.output)

    if result.success:
        print(f"Success: {result.message}")
        print(f"Processed {result.data['total_pages']} pages")
        print(f"Output directory: {result.data['output_dir']}")
        if result.data["has_diagrams"]:
            print("Diagrams were detected and enhanced")
    else:
        print(f"Error: {result.message}")
