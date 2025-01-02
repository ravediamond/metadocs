from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# Message analysis prompt
ANALYZE_TYPE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="Determine if a message is a question or modification request for a knowledge graph."
        ),
        HumanMessage(
            content="""Message: {message}

Return only JSON:
{
    "is_question": true/false
}"""
        ),
    ]
)

# Question handling prompt
QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="Answer questions about the knowledge graph using available data."
        ),
        HumanMessage(
            content="""Question: {message}
Available Data: {data}

Return only JSON:
{
    "content": "answer",
    "next_steps": ["follow-up questions"],
    "warnings": ["data limitations"]
}"""
        ),
    ]
)

# Modification handling prompt
MODIFICATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content="Process modification requests for the knowledge graph."),
        HumanMessage(
            content="""Request: {message}
Available Data: {data}

Return only JSON:
{
    "content": "response with impact analysis",
    "next_steps": ["implementation steps"],
    "warnings": ["potential risks"]
}"""
        ),
    ]
)
