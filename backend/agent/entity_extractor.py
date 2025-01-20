from typing import Tuple, Dict, List
import json
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

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


class EntityExtractor:
    def __init__(self, llm, max_iterations=3):
        self.llm = llm
        self.system_prompt = SYSTEM_PROMPT
        self.initial_entity_extraction_prompt = INITIAL_ENTITY_EXTRACTION_PROMPT
        self.iterative_extract_entities_prompt = ITERATIVE_ENTITY_EXTRACTION_PROMPT
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

    def extract_entities_and_relationships(
        self, content: str
    ) -> Tuple[Dict[str, Dict], List[Dict]]:
        """Extract entities and relationships from the given content."""
        all_entities, all_relationships = self._extract_entities_and_relationships(
            content
        )

        for _ in range(self.max_iterations - 1):
            new_entities, new_relationships = self._iterative_extraction(
                content, all_entities, all_relationships
            )
            all_entities.extend([e for e in new_entities if e not in all_entities])
            all_relationships.extend(
                [r for r in new_relationships if r not in all_relationships]
            )

        return {entity: {"name": entity} for entity in all_entities}, all_relationships
