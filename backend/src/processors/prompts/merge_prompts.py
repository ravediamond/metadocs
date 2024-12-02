SYSTEM_PROMPT = """You are an expert system specialized in analyzing and merging entity definitions."""

ENTITY_MERGE_PROMPT = """Analyze these entities and identify which ones should be merged.
Return only a list of entity IDs that should be merged due to:
1. Same concept with different names
2. Overlapping definitions
3. Parent-child relationships
4. Similar core characteristics

Format response as:
{
    "merged_entity_ids": ["id1", "id2", ...]
}"""

ENTITY_DETAILS_PROMPT = """For these merged entity IDs, create consolidated entity definitions.
Consider:
1. Combining characteristics
2. Resolving conflicts
3. Preserving unique attributes
4. Maintaining relationship context

Format each merged entity as per original schema."""
