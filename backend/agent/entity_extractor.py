from typing import Tuple, Dict, List
import json
import time
from functools import wraps
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

SYSTEM_PROMPT = """You are an expert system specialized in analyzing documents and extracting structured information about entities and their relationships. You are particularly thorough in identifying both direct and indirect relationships between entities."""
INITIAL_ENTITY_EXTRACTION_PROMPT = """Analyze the following markdown content and identify all important entities and their relationships.
An entity can be a person, organization, system, concept, process, or any other significant noun that plays a key role in the content.
Provide your response as a valid JSON object with two arrays:
1. "entities": array of unique entities found
2. "relationships": array of relationships between entities, where each relationship has:
   - "source": the source entity
   - "target": the target entity
   - "type": the type of relationship (e.g., "manages", "contains", "uses", "depends on")
   - "description": brief description of the relationship"""

ITERATIVE_ENTITY_EXTRACTION_PROMPT = """Given the following markdown content and the current state of identified entities and relationships, perform a thorough analysis to find:
1. Additional entities that might have been missed
2. Additional relationships between ALL entities (both new and previously identified)
3. Different types of relationships between entities that already have some connections
Current entities:
{previous_entities}
Current relationships:
{previous_relationships}
Consider the following in your analysis:
1. Entities:
   - Supporting or interacting components
   - Indirectly mentioned or implied entities
   - Dependencies or related systems
   - Sub-components or parent systems
   - Tools, resources, or artifacts involved
2. Relationships:
   - Direct interactions or dependencies
   - Indirect influences or impacts
   - Hierarchical relationships (part-of, contains, extends)
   - Temporal relationships (precedes, follows, triggers)
   - Data or resource flow relationships
   - Alternative relationship types between already-connected entities
   - Transitive relationships (if A relates to B and B to C, consider A to C)
Provide your response as a valid JSON object with two arrays:
1. "new_entities": array of additional unique entities found (not including previously identified ones)
2. "new_relationships": array of any new relationships discovered, including:
   - Relationships involving new entities
   - Additional relationships between existing entities
   - Alternative relationship types between already-connected entities
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


class EntityExtractor:
    def __init__(self, llm, max_iterations=3):
        self.llm = llm
        self.system_prompt = SYSTEM_PROMPT
        self.initial_entity_extraction_prompt = INITIAL_ENTITY_EXTRACTION_PROMPT
        self.iterative_extract_entities_prompt = ITERATIVE_ENTITY_EXTRACTION_PROMPT
        self.entity_details_prompt = ENTITY_DETAILS_PROMPT
        self.max_iterations = max_iterations

    def _extract_entities_and_relationships(
        self, content: str
    ) -> Tuple[Dict[str, Dict], List[Dict]]:
        """Extract entities and relationships from the given content."""
        try:
            prompt_content = [
                {"type": "text", "text": content},
                {"type": "text", "text": self.initial_entity_extraction_prompt},
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )
            chain = prompt | self.llm
            response = chain.invoke({})
            result = json.loads(response.content)
            return result["entities"], result["relationships"]
        except Exception as e:
            print(f"Error in entity and relationship extraction: {str(e)}")
            return {}, []

    def _iterative_extraction(
        self,
        content: str,
        previous_entities: List[str],
        previous_relationships: List[Dict],
    ) -> Tuple[List[str], List[Dict]]:
        """Perform another iteration of entity and relationship extraction."""
        try:
            formatted_relationships = "\n".join(
                f"- {rel['source']} {rel['type']} {rel['target']}: {rel['description']}"
                for rel in previous_relationships
            )
            prompt_content = [
                {"type": "text", "text": content},
                {
                    "type": "text",
                    "text": self.iterative_extract_entities_prompt.format(
                        previous_entities="\n".join(
                            f"- {entity}" for entity in previous_entities
                        ),
                        previous_relationships=formatted_relationships,
                    ),
                },
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )
            chain = prompt | self.llm
            response = chain.invoke({})
            result = json.loads(response.content)
            return result.get("new_entities", []), result.get("new_relationships", [])
        except Exception as e:
            print(f"Error in iterative extraction: {str(e)}")
            return [], []

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def extract_entity_details(self, entity: str, content: str) -> Dict:
        """Extract detailed information about the given entity."""
        try:
            prompt_content = [
                {"type": "text", "text": content},
                {
                    "type": "text",
                    "text": self.entity_details_prompt.format(entity=entity),
                },
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )
            chain = prompt | self.llm
            response = chain.invoke({})

            # Try to clean the response before parsing
            response_text = response.content.strip()
            try:
                # First try to parse as is
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If fails, try to find the first { and last }
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end != 0:
                    cleaned_response = response_text[start:end]
                    return json.loads(cleaned_response)
                raise
        except Exception as e:
            print(f"Error in entity details extraction for {entity}: {str(e)}")
            return {}

    def extract_entities_and_relationships(
        self, content: str
    ) -> Tuple[Dict[str, Dict], List[Dict]]:
        """Extract entities and relationships from the given content."""

        entity_details = {}

        all_entities, all_relationships = self._extract_entities_and_relationships(
            content
        )
        print(f"Initial entities: {all_entities}")

        for _ in range(self.max_iterations - 1):
            new_entities, new_relationships = self._iterative_extraction(
                content, all_entities, all_relationships
            )
            all_entities.extend([e for e in new_entities if e not in all_entities])
            all_relationships.extend(
                [r for r in new_relationships if r not in all_relationships]
            )

        for entity in all_entities:
            print(f"Extracting details for entity: {entity}")
            entity_detail = self.extract_entity_details(entity, content)
            entity_details[entity] = entity_detail

        return entity_details, all_relationships
