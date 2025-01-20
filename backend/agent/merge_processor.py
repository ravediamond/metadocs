import json
from typing import Dict, List
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
"""


class MergeProcessor:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SYSTEM_PROMPT
        self.entity_merge_prompt = ENTITY_MERGE_PROMPT

    def merge_entities_and_relationships(
        self, entities: Dict[str, Dict], relationships: List[Dict]
    ) -> List[Dict]:
        """Merge the given entities and relationships using the language model."""
        try:
            prompt_content = [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"entities": entities, "relationships": relationships}
                    ),
                },
                {"type": "text", "text": self.entity_merge_prompt},
            ]
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt_content),
                ]
            )
            print(prompt)
            chain = prompt | self.llm
            response = chain.invoke({})
            print(response)
            result = json.loads(response.content)
            return result
        except Exception as e:
            print(f"Error in entity and relationship merge: {str(e)}")
            return []
