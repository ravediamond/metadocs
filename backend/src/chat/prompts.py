from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""You are a helpful assistant that answers questions about a knowledge graph system by using the available tools to fetch and analyze data."""
        )
    ]
)
