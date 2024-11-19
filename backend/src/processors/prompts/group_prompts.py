SYSTEM_PROMPT = """You are an expert system specialized in analyzing and grouping related entities based on their characteristics, relationships, and semantic meaning."""

GROUP_ANALYSIS_PROMPT = """Analyze the provided entities and their relationships to identify meaningful groups and clusters.

Consider:
1. Entity types and categories
2. Relationship patterns
3. Semantic similarities
4. Functional relationships
5. Domain-specific groupings

Provide your response as a valid JSON object with:
{
    "groups": [
        {
            "name": "group name",
            "description": "group description",
            "type": "primary category of this group",
            "entities": ["entity1", "entity2"],
            "relationships": [
                {
                    "source": "entity1",
                    "target": "entity2",
                    "type": "relationship type",
                    "strength": "strong/medium/weak",
                    "evidence": "description of evidence"
                }
            ],
            "metadata": {
                "cohesion_score": 0-1,
                "key_characteristics": ["characteristic1", "characteristic2"],
                "tags": ["tag1", "tag2"]
            }
        }
    ],
    "cross_group_relationships": [
        {
            "source_group": "group1",
            "target_group": "group2",
            "type": "relationship type",
            "description": "relationship description",
            "strength": "strong/medium/weak"
        }
    ],
    "metrics": {
        "total_groups": number,
        "average_group_size": number,
        "isolation_score": 0-1,
        "interconnectedness_score": 0-1
    }
}"""
