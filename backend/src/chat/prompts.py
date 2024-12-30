from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# Message analysis prompt
ANALYZE_INTENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""You are a helpful assistant analyzing questions about a knowledge graph.
Your role is to classify the user's message and identify key elements."""
        ),
        HumanMessage(
            content="""Analyze if the following message is a question about the knowledge graph or a request to modify it.

Message: {message}

Examples:
- "What is the relationship between Contract and Invoice?" -> question about relationships
- "Entity X should be merged with Entity Y" -> modification request for merging
- "How many entities are in group Z?" -> question about groups
- "The hierarchy between A and B is wrong" -> modification request for hierarchy
- "Where does entity X appear in the sources?" -> question about sources
- "Add property 'status' to entity Contract" -> modification request for properties

ONLY RESPOND WITH A JSON OBJECT IN THIS EXACT FORMAT, NO OTHER TEXT:
{
    "type": "question or modification",
    "intent": "entity_relationship | entity_source | entity_group | entity_property | merge_request | hierarchy_change | etc",
    "target_entity": "main entity being discussed (null if none)",
    "related_entities": ["list of other entities mentioned (empty if none)"]
}"""
        ),
    ]
)

# Question analysis prompt
QUESTION_ANALYZER_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""You are a helpful assistant that determines what data is needed to answer a knowledge graph question.
You understand the pipeline stages: PARSE -> EXTRACT -> MERGE -> GROUP -> ONTOLOGY"""
        ),
        HumanMessage(
            content="""Based on this question and the available data sources, determine what needs to be loaded to provide an accurate answer.

Question: {message}
Intent: {intent}
Available versions: {available_versions}

Strategy tips:
- For entity relationships, check ONTOLOGY first, then MERGE
- For source questions, check PARSE outputs
- For group questions, check GROUP and MERGE
- Always start with the most processed data (ONTOLOGY -> PARSE)

ONLY RESPOND WITH A JSON OBJECT IN THIS EXACT FORMAT, NO OTHER TEXT:
{
    "required_data": ["list of version types needed"],
    "reasoning": "explanation of why these are needed",
    "load_order": ["optimal order to load and check the data"]
}"""
        ),
    ]
)

# Modification analysis prompt
MODIFICATION_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""You are a helpful assistant analyzing requested modifications to a knowledge graph.
You help determine what changes are needed and their potential impact."""
        ),
        HumanMessage(
            content="""Analyze this modification request and the current state to determine what needs to be changed.

Request: {message}
Current State: {current_state}

Consider:
- Impact on existing relationships
- Effects on groups
- Changes to hierarchy
- Data consistency

ONLY RESPOND WITH A JSON OBJECT IN THIS EXACT FORMAT, NO OTHER TEXT:
{
    "changes_needed": [
        {
            "type": "merge|split|property|relationship|group|hierarchy",
            "description": "specific change needed",
            "affected_entities": ["list of affected entities"],
            "stage": "which stage needs to be modified"
        }
    ],
    "impact_analysis": {
        "complexity": "high|medium|low",
        "scope": "local|connected|global",
        "risks": ["potential risks"],
        "dependencies": ["affected aspects of the graph"]
    }
}"""
        ),
    ]
)

# Response generation prompt
RESPONSE_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""You are a helpful assistant that generates clear responses about a knowledge graph.
You explain things clearly and provide context when needed."""
        ),
        HumanMessage(
            content="""Generate a response based on the analysis results and loaded data.

User Message: {message}
Intent: {intent}
Analysis Results: {analysis}
Loaded Data: {loaded_data}

Guidelines:
- Be clear and concise
- Explain reasoning when relevant
- For modifications, explain the impact
- For questions, provide context
- Suggest related queries when helpful

ONLY RESPOND WITH A JSON OBJECT IN THIS EXACT FORMAT, NO OTHER TEXT:
{
    "response": "the main response message",
    "suggestions": ["optional related questions or actions"],
    "warnings": ["any important caveats or warnings"]
}"""
        ),
    ]
)

# Todo item creation prompt
TODO_ITEM_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="You are a helpful assistant that creates clear todo items for knowledge graph modifications."
        ),
        HumanMessage(
            content="""Create a todo item based on the approved modification.

Modification: {modification}
Impact Analysis: {impact_analysis}

ONLY RESPOND WITH A JSON OBJECT IN THIS EXACT FORMAT, NO OTHER TEXT:
{
    "title": "brief description",
    "description": "detailed explanation",
    "affected_stages": ["list of affected pipeline stages"],
    "priority": "high|medium|low",
    "estimated_complexity": "high|medium|low",
    "required_actions": ["specific steps needed"]
}"""
        ),
    ]
)
