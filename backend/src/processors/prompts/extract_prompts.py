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
