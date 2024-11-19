
SYSTEM_PROMPT = """You are an expert system specialized in generating Mermaid diagrams to represent ontological relationships and hierarchies."""

MERMAID_GENERATION_PROMPT = """Generate a Mermaid class diagram representing the ontology of entities and their groups.

Rules:
1. Use classes for entities and groups
2. Show relationships between entities
3. Show group memberships
4. Include important attributes
5. Use appropriate relationship types (--|>, --|o, -->, o--, etc.)
6. Add meaningful labels to relationships
7. Use colors and styles to differentiate groups

The diagram should follow this structure:
```mermaid
classDiagram
    %% Group definitions with distinct colors
    class GroupName {
        +type: string
        +description: string
    }
    
    %% Entity definitions with attributes
    class EntityName {
        +category: string
        +key_characteristics
    }
    
    %% Relationships
    GroupName --* EntityName : contains
    EntityName --> EntityName : relates_to
```"""