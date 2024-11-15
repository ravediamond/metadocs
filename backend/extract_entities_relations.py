from dataclasses import dataclass
from typing import List, Dict, Optional, Set
import json
import logging
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import os
from datetime import datetime
import concurrent.futures
from pathlib import Path

SYSTEM_PROMPT = """You are an expert system specialized in analyzing documents and extracting structured information about entities and their relationships."""

INITIAL_ENTITY_EXTRACTION_PROMPT = """Analyze the following markdown content and identify all important entities and their relationships.
An entity can be a person, organization, system, concept, process, or any other significant noun that plays a key role in the content.

Provide your response as a valid JSON object with two arrays:
1. "entities": array of unique entities found
2. "relationships": array of relationships between entities, where each relationship has:
   - "source": the source entity
   - "target": the target entity
   - "type": the type of relationship (e.g., "manages", "contains", "uses", "depends on")
   - "description": brief description of the relationship"""

ITERATIVE_ENTITY_EXTRACTION_PROMPT = """Given the following markdown content and the list of previously identified entities, analyze the content again to find any additional entities that might have been missed. Consider entities that:
1. Support or interact with the known entities
2. Are mentioned indirectly or implicitly
3. Represent components, dependencies, or related systems
4. Are part of the broader ecosystem described

Previously identified entities:
{previous_entities}

Provide your response as a valid JSON object with two arrays:
1. "new_entities": array of additional unique entities found (not including previously identified ones)
2. "new_relationships": array of any new relationships discovered, including relationships involving both new and previously identified entities

Each relationship should have:
- "source": the source entity
- "target": the target entity
- "type": the type of relationship
- "description": brief description of the relationship"""

ENTITY_DETAILS_PROMPT = """Analyze the following markdown content and provide detailed information about the entity: {entity}

Focus on:
1. Definition and purpose
2. Key characteristics
3. Main functions or responsibilities
4. Important attributes
5. Any constraints or limitations
6. Related technologies or concepts

Provide your response as a valid JSON object with these fields:
{{
    "name": "exact entity name",
    "category": "type of entity (e.g., system, person, process)",
    "definition": "clear definition",
    "characteristics": ["list", "of", "key", "characteristics"],
    "functions": ["list", "of", "main", "functions"],
    "attributes": ["list", "of", "important", "attributes"],
    "constraints": ["list", "of", "constraints"],
    "related_concepts": ["list", "of", "related", "concepts"]
}}"""


@dataclass
class Entity:
    name: str
    category: str
    definition: str
    characteristics: List[str]
    functions: List[str]
    attributes: List[str]
    constraints: List[str]
    related_concepts: List[str]


@dataclass
class Relationship:
    source: str
    target: str
    type: str
    description: str


@dataclass
class AnalysisResult:
    entities: Dict[str, Entity]
    relationships: List[Relationship]


def setup_logging(output_dir: str) -> logging.Logger:
    """Setup logging configuration."""
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    logger = logging.getLogger("MarkdownAnalyzer")
    logger.setLevel(logging.DEBUG)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, f"markdown_analyzer_{timestamp}.log")
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def initial_entity_extraction(
    model: ChatBedrock, markdown_content: str, logger: logging.Logger
) -> tuple[List[str], List[Dict]]:
    """Perform initial extraction of entities and relationships."""
    logger.info("Performing initial entity extraction")

    try:
        content = [
            {"type": "text", "text": markdown_content},
            {"type": "text", "text": INITIAL_ENTITY_EXTRACTION_PROMPT},
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )

        chain = prompt | model
        response = chain.invoke({})
        result = json.loads(response.content)

        logger.info(
            f"Initial extraction found {len(result['entities'])} entities and {len(result['relationships'])} relationships"
        )
        return result["entities"], result["relationships"]

    except Exception as e:
        logger.error(f"Error in initial entity extraction: {str(e)}")
        raise


def iterative_entity_extraction(
    model: ChatBedrock,
    markdown_content: str,
    previous_entities: List[str],
    logger: logging.Logger,
) -> tuple[List[str], List[Dict]]:
    """Perform another iteration of entity extraction, considering previously found entities."""
    logger.info("Performing iterative entity extraction")

    try:
        content = [
            {"type": "text", "text": markdown_content},
            {
                "type": "text",
                "text": ITERATIVE_ENTITY_EXTRACTION_PROMPT.format(
                    previous_entities="\n".join(
                        [f"- {entity}" for entity in previous_entities]
                    )
                ),
            },
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )

        chain = prompt | model
        response = chain.invoke({})
        result = json.loads(response.content)

        logger.info(
            f"Iteration found {len(result.get('new_entities', []))} new entities and {len(result.get('new_relationships', []))} new relationships"
        )
        return result.get("new_entities", []), result.get("new_relationships", [])

    except Exception as e:
        logger.error(f"Error in iterative entity extraction: {str(e)}")
        raise


def get_entity_details(
    model: ChatBedrock, entity: str, markdown_content: str, logger: logging.Logger
) -> Entity:
    """Get detailed information about a specific entity."""
    logger.info(f"Getting details for entity: {entity}")

    try:
        content = [
            {"type": "text", "text": markdown_content},
            {"type": "text", "text": ENTITY_DETAILS_PROMPT.format(entity=entity)},
        ]

        prompt = ChatPromptTemplate.from_messages(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
        )

        chain = prompt | model
        response = chain.invoke({})
        result = json.loads(response.content)

        return Entity(
            name=result["name"],
            category=result["category"],
            definition=result["definition"],
            characteristics=result["characteristics"],
            functions=result["functions"],
            attributes=result["attributes"],
            constraints=result["constraints"],
            related_concepts=result["related_concepts"],
        )

    except Exception as e:
        logger.error(f"Error getting details for entity {entity}: {str(e)}")
        raise


def analyze_markdown(
    markdown_path: str, iterations: int = 3, output_dir: str = "analysis_output"
) -> Optional[str]:
    """Analyze markdown content with multiple iterations of entity extraction."""
    logger = setup_logging(output_dir)
    logger.info(
        f"Starting markdown analysis for {markdown_path} with {iterations} iterations"
    )

    try:
        # Initialize model
        logger.info("Initializing Bedrock model")
        model = ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="us-east-1",
            model_kwargs=dict(temperature=0, max_tokens=4096),
        )

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Read markdown content
        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # Initial extraction
        all_entities, all_relationships = initial_entity_extraction(
            model, markdown_content, logger
        )

        # Iterative extractions
        for i in range(iterations - 1):
            logger.info(f"Starting iteration {i + 2} of {iterations}")
            new_entities, new_relationships = iterative_entity_extraction(
                model, markdown_content, all_entities, logger
            )

            # Add new unique entities and relationships
            all_entities.extend([e for e in new_entities if e not in all_entities])
            all_relationships.extend(new_relationships)

        # Get detailed information for each entity
        entity_details = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_entity = {
                executor.submit(
                    get_entity_details, model, entity, markdown_content, logger
                ): entity
                for entity in all_entities
            }

            for future in concurrent.futures.as_completed(future_to_entity):
                entity = future_to_entity[future]
                try:
                    entity_info = future.result()
                    entity_details[entity] = {
                        "category": entity_info.category,
                        "definition": entity_info.definition,
                        "characteristics": entity_info.characteristics,
                        "functions": entity_info.functions,
                        "attributes": entity_info.attributes,
                        "constraints": entity_info.constraints,
                        "related_concepts": entity_info.related_concepts,
                    }
                except Exception as e:
                    logger.error(f"Error processing entity {entity}: {str(e)}")

        # Prepare final analysis
        analysis = {
            "entities": entity_details,
            "relationships": all_relationships,
            "metadata": {
                "iterations": iterations,
                "total_entities": len(all_entities),
                "total_relationships": len(all_relationships),
            },
        }

        # Save analysis to file
        output_file = os.path.join(output_dir, "entity_analysis.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        logger.info(f"Analysis completed and saved to {output_file}")
        return output_file

    except Exception as e:
        logger.error(f"Error during markdown analysis: {str(e)}", exc_info=True)
        return None
    finally:
        logger.info("Closing logging handlers")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze markdown content and extract entity information"
    )
    parser.add_argument(
        "markdown_path", type=str, help="Path to the markdown file to analyze"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations for entity extraction (default: 3)",
    )
    parser.add_argument(
        "--output", type=str, default="analysis_output", help="Output directory path"
    )

    args = parser.parse_args()
    output_file = analyze_markdown(args.markdown_path, args.iterations, args.output)

    if output_file:
        print(f"Analysis completed successfully. Results saved to: {output_file}")
    else:
        print("Analysis failed. Check logs for details.")
