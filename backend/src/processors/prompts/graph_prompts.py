SYSTEM_PROMPT = """You are a knowledge graph processing assistant. Your role is to:
1. Analyze extracted entities and relationships
2. Create a cohesive knowledge graph
3. Identify and merge similar entities
4. Create logical groupings
5. Generate appropriate visualizations

Format your response as a JSON object with:
{
    "graph": {
        "entities": [
            {
                "id": "unique_id",
                "name": "entity_name",
                "category": "entity_category",
                "properties": {},
                "groups": ["group1", "group2"]
            }
        ],
        "relationships": [
            {
                "source": "source_id",
                "target": "target_id",
                "type": "relationship_type",
                "properties": {}
            }
        ],
        "groups": [
            {
                "name": "group_name",
                "description": "group_description",
                "entities": ["entity_id1", "entity_id2"]
            }
        ]
    },
    "visualization": {
        "type": "mermaid",
        "content": "graph visualization in mermaid format",
        "title": "Knowledge Graph"
    },
    "metadata": {
        "entity_count": 0,
        "relationship_count": 0,
        "group_count": 0,
        "validation_errors": []
    }
}"""

ENTITY_ANALYSIS_PROMPT = """Analyze the following extracted entities and their relationships:

{entities_data}

Create a unified knowledge graph by:
1. Merging similar entities
2. Standardizing relationship types
3. Creating logical groupings
4. Validating entity relationships

Return the results in the specified JSON format."""

VISUALIZATION_PROMPT = """Generate a Mermaid diagram for the following graph structure:

{graph_data}

Focus on:
1. Clear entity relationships
2. Logical groupings
3. Important properties
4. Key relationships

Use appropriate Mermaid syntax for class and relationship diagrams."""

VALIDATION_PROMPT = """Validate the following knowledge graph:

{graph_data}

Check for:
1. Consistency in entity naming
2. Valid relationship types
3. Proper grouping structure
4. Missing or invalid properties

Return any validation errors or suggestions for improvement."""

UPDATE_PROMPT = """Update the knowledge graph based on the following feedback:

Current Graph:
{current_graph}

Feedback:
{feedback}

Make necessary adjustments while maintaining graph integrity and consistency."""
