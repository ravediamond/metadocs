import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = (
    "You are an expert system specialized in analyzing and merging entity definitions."
)
ENTITY_MERGE_PROMPT = """Analyze these entities and relationships, and identify which ones should be merged.
Return a list of merged entities, where each merged entity contains the following fields:
- "name": the consolidated name for the merged entity
- "category": the category of the merged entity (e.g., "system", "person", "process")
- "definition": a clear definition of the merged entity
- "characteristics": a list of key characteristics of the merged entity
- "functions": a list of main functions or responsibilities of the merged entity
- "attributes": a list of important attributes of the merged entity
- "constraints": a list of constraints or limitations of the merged entity
- "related_concepts": a list of related concepts or technologies to the merged entity
Merge entities based on:
1. Same concept with different names
2. Overlapping definitions
3. Parent-child relationships
4. Similar core characteristics

Important point: 
Don't tell me what you are going to do like this "I\'ll analyze the entities and relationships and propose merged entities. Here are the key consolidations:", only give me the result as json.

Here's the output format:
{
  "merged": [
    {
      "name": "merged_entity_name",
      "category": "entity_category",
      "definition": "merged_definition",
      "characteristics": ["char1", "char2"],
      "functions": ["func1", "func2"],
      "attributes": ["attr1", "attr2"],
      "constraints": ["constraint1", "constraint2"],
      "related_concepts": ["concept1", "concept2"]
    }
  ]
}
"""

PLANNING_PROMPT = """Analyze these entities and relationships from different files and create a merging plan.
For each file, you'll receive its entities and relationships with the file path.
Return a list of planned merges, where each merge contains:
- "result_name": the final name for the merged entity/relationship
- "type": either "entity" or "relationship"
- "sources": list of objects containing:
  - "file_path": the source file path
  - "name": name of entity/relationship in that file
- "reason": brief explanation of why these should be merged

Return the result as JSON with two keys:
- "planned_entity_merges": list of entity merge plans
- "planned_relationship_merges": list of relationship merge plans

Focus on identifying:
1. Same concepts with different names across files
2. Overlapping definitions
3. Parent-child relationships that should be combined
4. Similar core characteristics

Important point: 
Don't tell me what you are going to do like this "I\'ll analyze the entities and relationships from the provided file.", only give me the result as json.

Here's the output format:
{
  "planned_entity_merges": [
    {
      "result_name": "merged_entity_name",
      "type": "entity",
      "sources": [
        {
          "file_path": "file_path",
          "name": "entity_name"
        },
        {
          "file_path": "file_path",
          "name": "entity_name"
        }
      ],
      "reason": "brief explanation"
    }
  ],
  "planned_relationship_merges": [
    {
      "result_name": "merged_relationship_name",
      "type": "relationship",
      "sources": [
        {
          "file_path": "file_path",
          "name": "relationship_name"
        },
        {
          "file_path": "file_path",
          "name": "relationship_name"
        }
      ],
      "reason": "brief explanation"
    }
  ]
}
"""


@dataclass
class MergeSource:
    file_path: str
    name: str


@dataclass
class PlannedMerge:
    result_name: str
    type: str
    sources: List[MergeSource]
    reason: str


class MergeProcessor:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SYSTEM_PROMPT
        self.entity_merge_prompt = ENTITY_MERGE_PROMPT
        self.planning_prompt = PLANNING_PROMPT

    def plan_merges(
        self, entities_relationships: Dict[str, Dict[str, Dict]]
    ) -> Tuple[List[PlannedMerge], List[PlannedMerge]]:
        """Create a merge plan for entities and relationships."""

        try:
            # Prepare input data with file information preserved
            input_data = {
                "files": [
                    {
                        "file_path": file_path,
                        "entities": file_data.get("entities", {}),
                        "relationships": file_data.get("relationships", []),
                    }
                    for file_path, file_data in entities_relationships.items()
                ]
            }

            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": json.dumps(input_data)},
                            {"type": "text", "text": self.planning_prompt},
                        ]
                    ),
                ]
            )

            chain = prompt | self.llm
            response = chain.invoke({})
            result = json.loads(response.content)

            # Convert the planning results to PlannedMerge objects
            entity_merges = [
                PlannedMerge(
                    result_name=plan["result_name"],
                    type="entity",
                    sources=[MergeSource(**source) for source in plan["sources"]],
                    reason=plan["reason"],
                )
                for plan in result.get("planned_entity_merges", [])
            ]

            relationship_merges = [
                PlannedMerge(
                    result_name=plan["result_name"],
                    type="relationship",
                    sources=[MergeSource(**source) for source in plan["sources"]],
                    reason=plan["reason"],
                )
                for plan in result.get("planned_relationship_merges", [])
            ]

            return entity_merges, relationship_merges

        except Exception as e:
            print(f"Error in merge planning: {str(e)}")
            return [], []

    def execute_merge_plan(
        self,
        entities_relationships: Dict[str, Dict[str, Dict]],
        entity_merges: List[PlannedMerge],
        relationship_merges: List[PlannedMerge],
    ) -> Tuple[List[Dict], List[Dict]]:
        """Execute the merge plan iteratively for entities and relationships."""
        try:
            merged_entities = []
            merged_relationships = []

            # Process entity merges iteratively
            for merge in entity_merges:
                merger_input = {
                    "plan": {
                        "sources": [
                            {
                                "file_path": source.file_path,
                                "name": source.name,
                                "data": entities_relationships[source.file_path][
                                    "entities"
                                ].get(source.name, {}),
                            }
                            for source in merge.sources
                        ],
                        "result_name": merge.result_name,
                    }
                }

                prompt = ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(
                            content=[
                                {"type": "text", "text": json.dumps(merger_input)},
                                {"type": "text", "text": self.entity_merge_prompt},
                            ]
                        ),
                    ]
                )

                chain = prompt | self.llm
                response = chain.invoke({})
                print("Response entity:", response.content)
                result = json.loads(response.content)
                merged_entities.append(result["merged"][0])

            # Process relationship merges iteratively
            for merge in relationship_merges:
                merger_input = {
                    "plan": {
                        "sources": [
                            {
                                "file_path": source.file_path,
                                "name": source.name,
                                "data": next(
                                    (
                                        r
                                        for r in entities_relationships[
                                            source.file_path
                                        ].get("relationships", [])
                                        if r.get("name") == source.name
                                    ),
                                    {},
                                ),
                            }
                            for source in merge.sources
                        ],
                        "result_name": merge.result_name,
                    }
                }

                prompt = ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(
                            content=[
                                {"type": "text", "text": json.dumps(merger_input)},
                                {"type": "text", "text": self.entity_merge_prompt},
                            ]
                        ),
                    ]
                )

                chain = prompt | self.llm
                response = chain.invoke({})
                print("Response relationship:", response.content)
                result = json.loads(response.content)
                merged_relationships.append(result["merged"][0])

            return merged_entities, merged_relationships

        except Exception as e:
            print(f"Error in executing merge plan: {str(e)}")
            return [], []

    def merge_entities_and_relationships(
        self, entities_relationships: Dict[str, Dict[str, Dict]]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Two-phase merge process: planning and execution."""
        entity_merges, relationship_merges = self.plan_merges(entities_relationships)

        merged_entities, merged_relationships = self.execute_merge_plan(
            entities_relationships, entity_merges, relationship_merges
        )

        return merged_entities, merged_relationships
