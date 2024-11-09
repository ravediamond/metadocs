from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from typing import List, Optional
from PIL import Image
import base64
from io import BytesIO
from pdf2image import convert_from_path
import json


class ParsedContent(BaseModel):
    id: str
    group_title: Optional[str] = None
    content: Optional[str] = None
    elements: Optional[str] = None


class Entity(BaseModel):
    entity_name: str
    related_data: Optional[str] = None
    related_content_ids: Optional[List[str]] = None
    parent_entity: Optional[str] = None


class OutputSchema(BaseModel):
    parsed_content: List[ParsedContent]
    entities: List[Entity]


# Define the prompt for the GPT-4 Vision model
prompt_text = """
You will be provided with an image that may contain text, diagrams, architecture diagrams, slides, or a combination of these elements related to a specific domain.

Your task is to analyze the image and extract structured information according to the following steps:

1. Extract Information from the Image:
   - Analyze the image using your vision capabilities.
   - Identify and interpret all textual content, diagrams, and visual elements.
   - Separate the content into logical groups or sections based on titles, headings, subheadings, or thematic breaks.
   - Assign a unique identifier (`id`) to each group or section for reference purposes.
   - Understand the hierarchical structure implied by titles and headings, where titles and headings indicate parent entities, and the content or entities listed under them are child entities.
   - For graphs and tables, provide detailed descriptions and context.

2. Identify Entities and Their Hierarchical Relationships:
   - Identify all entities mentioned in both textual and visual content. Entities can include concepts, methodologies, data sources, products, metrics, components in diagrams, or any domain-specific terms.
   - For each entity, gather any directly related data, descriptions, or relationships provided in the image.
   - Determine the hierarchical relationships between entities based on the structure implied by titles and headings.
   - Link each entity to the relevant parts of the parsed content using the `id`s assigned to the groups or sections.
"""

system_prompt = """
You are an AI language model with advanced vision capabilities specialized in analyzing images containing text, diagrams, architecture diagrams, slides, or combinations of these elements related to various domains.

Your primary objectives are:

- Accurately extract and interpret all textual and visual information from the provided images.
- Identify entities, their related data, and hierarchical relationships based on the document structure implied by titles and headings.
- Produce a structured JSON output that conforms strictly to the provided Pydantic models.

Guidelines:

- Pay close attention to the hierarchical structure of the content. Titles and headings indicate parent entities, while the content or entities listed under them are child entities.
- Assign unique integer identifiers (`id`) to each content section for reference purposes.
- Ensure that all entities are linked to the relevant content sections using these `id`s.
- Clearly define parent and child relationships between entities.
- Focus on accuracy and completeness in both text and visual information extraction.
- Do not include any additional commentary or explanations outside of the JSON structure.
- The final output should be a single JSON object that adheres strictly to the provided schema.

Your response should only contain the JSON output as per the specified `OutputSchema`.
"""

openai_key = ""

# Initialize the LLM for GPT-4 Vision
model = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=openai_key,
)
structured_llm = model.with_structured_output(OutputSchema)

pdf_path = "test2.pdf"
all_responses = []
max_pages = 12

pages = convert_from_path(pdf_path, dpi=300)

for page_num, image in enumerate(pages[:max_pages], start=1):
    # Resize the image if necessary
    image = image.resize((512, 512))

    # Show image
    # image.show(title=f"Page {page_num}")

    # Convert image to base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # Create the prompt for this page
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                ]
            ),
        ]
    )

    # Initialize the chain for processing
    chain = prompt | structured_llm

    try:
        response = chain.invoke({})
        # Format response data for JSON storage
        formatted_response = {
            "page": page_num,
            "parsed_content": [pc.dict() for pc in response.parsed_content],
            "entities": [entity.dict() for entity in response.entities],
        }
        all_responses.append(formatted_response)
    except Exception as e:
        print(f"Error processing page {page_num}: {e}")
        continue

# Save the collected output to a JSON file
with open("output_data.json", "w") as f:
    json.dump(all_responses, f, indent=4)

print("Processing complete. Results saved to 'output_data.json'.")
