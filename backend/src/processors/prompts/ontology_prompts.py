SYSTEM_PROMPT = """You are an expert system specialized in generating Mermaid diagrams to represent ontological relationships and hierarchies."""

ONTOLOGY_PROMPT = """Generate a JSON object containing Mermaid class diagram code representing the ontology of entities and their groups. The output should be a JSON object with a single key called "ontology" whose value is the Mermaid diagram code.

Rules:
1. Use classes for entities and groups
2. Show relationships between entities
3. Show group memberships
4. Include important attributes
5. Use appropriate relationship types (--|>, --|o, -->, o--, etc.)
6. Add meaningful labels to relationships
7. Use colors and styles to differentiate groups

The output should follow this structure:
{
    "ontology": "classDiagram\\n    %% Group definitions with distinct colors\\n    class GroupName {\\n        +type: string\\n        +description: string\\n    }\\n\\n    %% Entity definitions with attributes\\n    class EntityName {\\n        +category: string\\n        +key_characteristics\\n    }\\n\\n    %% Relationships\\n    GroupName --* EntityName : contains\\n    EntityName --> EntityName : relates_to"
}
"""
