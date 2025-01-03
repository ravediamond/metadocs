from typing import TypedDict, List, Any, Dict, Annotated
from uuid import UUID
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    """State definition for the graph assistant"""

    messages: Annotated[List[BaseMessage], add_messages]
    tenant_id: UUID
    domain_id: UUID
    versions: Dict[str, Any]
    domain_info: Dict[str, Any]
    file_info: Dict[str, Any]
    db: Any
