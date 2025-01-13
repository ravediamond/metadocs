import fitz
from PIL import Image
import base64
from io import BytesIO
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage


class PDFParser:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = """You are an advanced vision-capable assistant specialized in analyzing and transforming visual content."""
        self.convert_prompt = """Convert the image content to clear and well-structured markdown.
Focus on:
1. Maintaining document structure with proper headings
2. Preserving important formatting
3. Converting tables and lists correctly
4. Capturing all relevant content accurately
5. Using appropriate markdown syntax for:
   - Headers (# for main titles, ## for sections)
   - Lists (- for bullet points, 1. for numbered)
   - Tables (| for columns)
   - Code blocks (```)
   - Emphasis (**bold**, *italic*)"""

    def _convert_page_to_image(self, page: fitz.Page) -> Image.Image:
        """Convert PDF page to PIL Image."""
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    def _encode_image(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG", quality=95)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _process_page(self, image: Image.Image) -> str:
        """Process a single page and return markdown content."""
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{self._encode_image(image)}"
                },
            },
            {"type": "text", "text": self.convert_prompt},
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=self.system_prompt), HumanMessage(content=content)]
        )

        chain = prompt | self.llm
        response = chain.invoke({})
        return response.content

    def parse_pdf(self, pdf_path: str) -> str:
        """Parse PDF file to markdown."""
        try:
            doc = fitz.open(pdf_path)
            markdown_content = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                image = self._convert_page_to_image(page)
                content = self._process_page(image)
                markdown_content.append(f"## Page {page_num + 1}\n\n{content}")

            return "\n\n---\n\n".join(markdown_content)

        except Exception as e:
            return f"Error processing PDF: {str(e)}"
