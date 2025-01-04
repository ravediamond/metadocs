import logging
from datetime import datetime
from typing import TypedDict, List, Any, Dict, Annotated
from uuid import UUID
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from .tools import create_data_loading_tools
from ..models.models import Domain, DomainVersionFile, FileVersion, File
from .prompts import CHAT_PROMPT  # Import the CHAT_PROMPT

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class State(TypedDict):
    """State definition for the graph assistant"""

    messages: Annotated[List[BaseMessage], add_messages]
    tenant_id: UUID
    domain_id: UUID
    versions: Dict[str, Any]
    domain_info: Dict[str, Any]
    file_info: Dict[str, Any]
    db: Any


class GraphAssistant:
    def __init__(self, llm_client, db):
        # Bind tools to LLM
        self.llm = llm_client.bind_tools(create_data_loading_tools(db))
        self.db = db
        self.graph = self._create_graph()

    def _get_domain_info(self, domain_id: UUID) -> dict:
        """Get domain information at initialization"""
        domain = self.db.query(Domain).filter_by(domain_id=domain_id).first()
        if not domain:
            return {}
        return {
            "name": domain.domain_name,
            "description": domain.description,
            "created_at": domain.created_at,
            "owner_id": domain.owner_user_id,
        }

    def _get_files_info(self, domain_id: UUID) -> dict:
        """Get file information at initialization"""
        files = (
            self.db.query(DomainVersionFile, FileVersion, File)
            .join(
                FileVersion,
                DomainVersionFile.file_version_id == FileVersion.file_version_id,
            )
            .join(File, FileVersion.file_id == File.file_id)
            .filter(DomainVersionFile.domain_id == domain_id)
            .all()
        )

        if not files:
            return {}

        return {
            file_version.file_version_id: {
                "name": file.filename,
                "file_type": file_version.file_type,
                "created_at": file_version.created_at,
                "version_number": file_version.version_number,
                "file_size": file_version.file_size,
            }
            for domain_version_file, file_version, file in files
        }

    def _format_domain_and_files(self, state):
        """Format domain and files information for the prompt"""
        domain_info = state.get("domain_info", {})
        files_info = state.get("file_info", {})

        domain_section = f"""Domain: {domain_info.get('name')}
- Description: {domain_info.get('description')}
- Created: {domain_info.get('created_at')}"""

        files_section = []
        for file_id, file_data in files_info.items():
            entry = f"""File: {file_data.get('name')}
- File Version ID: {file_id}
- Type: {file_data.get('file_type')}
- Version: {file_data.get('version_number')}
- Created: {file_data.get('created_at')}"""
            files_section.append(entry)

        return domain_section + "\n\n" + "\n\n".join(files_section)

    def _create_graph(self):
        builder = StateGraph(State)

        def chatbot(state: State):
            print(f"\n=== Chatbot Node ===")
            versions = state.get("versions", {})

            # Prepare prompt inputs
            prompt_inputs = {
                "messages": state["messages"],
                "domain_and_files": self._format_domain_and_files(state),
                "parse_versions": versions.get("parse_versions", []),
                "extract_versions": versions.get("extract_versions", []),
                "merge_version": versions.get("merge_version"),
                "group_version": versions.get("group_version"),
                "ontology_version": versions.get("ontology_version"),
            }

            # Format messages using the template
            messages = CHAT_PROMPT.format_messages(**prompt_inputs)

            # Invoke LLM with formatted messages
            response = self.llm.invoke(messages)
            return {"messages": [response]}

        builder.add_node("chatbot", chatbot)

        tool_node = ToolNode(tools=create_data_loading_tools(self.db))
        builder.add_node("tools", tool_node)

        def route_tools(state: State):
            print(f"\n=== Router ===")
            print(f"Current state: {state}")
            if messages := state.get("messages", []):
                last_msg = messages[-1]
                if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
                    print("Routing to: tools")
                    return "tools"
            print("Routing to: end")
            return "__end__"

        builder.add_conditional_edges(
            "chatbot", route_tools, {"tools": "tools", "__end__": "__end__"}
        )
        builder.add_edge("tools", "chatbot")
        builder.set_entry_point("chatbot")

        return builder.compile()

    async def process_message(self, state_dict):
        try:
            print("\n=== New Message Processing ===")
            print(f"Initial state: {state_dict}")

            # Initialize domain and file info if not present
            if not state_dict.get("domain_info"):
                state_dict["domain_info"] = self._get_domain_info(
                    state_dict["domain_id"]
                )
            if not state_dict.get("file_info"):
                state_dict["file_info"] = self._get_files_info(state_dict["domain_id"])

            state = {
                "messages": state_dict["messages"],
                "tenant_id": state_dict["tenant_id"],
                "domain_id": state_dict["domain_id"],
                "versions": state_dict["versions"],
                "domain_info": state_dict["domain_info"],
                "file_info": state_dict["file_info"],
                "db": self.db,
            }

            result = await self.graph.ainvoke(state)
            print(f"\n=== Final Result ===")
            print(f"Result: {result}")

            return {
                "message_type": "TEXT",
                "intent": "ANALYZE_RESULTS",
                "response": result["messages"][-1].content,
                "suggestions": [],
                "warnings": [],
            }

        except Exception as e:
            print(f"\n=== Error ===")
            print(f"Error processing message: {str(e)}")
            return {
                "message_type": "ERROR",
                "intent": "ERROR",
                "response": f"Error processing message: {str(e)}",
                "warnings": [str(e)],
            }
