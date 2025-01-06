import logging
import json
from datetime import datetime
from typing import TypedDict, List, Any, Dict, Annotated
from uuid import UUID
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from .tools import create_data_loading_tools
from ..models.models import Domain, DomainVersionFile, FileVersion, File
from .prompts import CHAT_PROMPT
from .visualization import generate_visualization

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tenant_id: UUID
    domain_id: UUID
    versions: Dict[str, Any]
    domain_info: Dict[str, Any]
    file_info: Dict[str, Any]
    db: Any


class GraphAssistant:
    def __init__(self, llm_client, db):
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
- Type: {file_data.get('file_type')}
- Version: {file_data.get('version_number')}"""
            files_section.append(entry)

        return domain_section + "\n\n" + "\n\n".join(files_section)

    def _create_graph(self):
        builder = StateGraph(State)

        # Chatbot node - processes initial message
        def chatbot(state: State):
            versions = state.get("versions", {})
            prompt_inputs = {
                "messages": state["messages"],
                "domain_and_files": self._format_domain_and_files(state),
                "parse_versions": versions.get("parse_versions", []),
                "extract_versions": versions.get("extract_versions", []),
                "merge_version": versions.get("merge_version"),
                "group_version": versions.get("group_version"),
                "ontology_version": versions.get("ontology_version"),
            }
            messages = CHAT_PROMPT.format_messages(**prompt_inputs)
            response = self.llm.invoke(messages)
            return {"messages": [response]}

        # Tools node - handles data loading operations
        tool_node = ToolNode(tools=create_data_loading_tools(self.db))

        # Visualization node - generates visualizations based on content
        def visualization(state: State):
            messages = state.get("messages", [])
            if not messages:
                return state

            last_msg = messages[-1]
            viz_data = generate_visualization(last_msg.content, state)

            return state

        # Add nodes
        builder.add_node("chatbot", chatbot)
        builder.add_node("tools", tool_node)
        builder.add_node("visualization", visualization)

        # Router function
        def route(state: State):
            if messages := state.get("messages", []):
                last_msg = messages[-1]
                if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
                    return "tools"
                return "visualization"
            return "__end__"

        # Add edges
        builder.add_conditional_edges(
            "chatbot",
            route,
            {"tools": "tools", "visualization": "visualization", "__end__": "__end__"},
        )
        builder.add_edge("tools", "chatbot")
        builder.add_edge("visualization", "__end__")
        builder.set_entry_point("chatbot")

        return builder.compile()

    async def process_message(self, state_dict):
        try:
            state = {
                "messages": state_dict["messages"],
                "tenant_id": state_dict["tenant_id"],
                "domain_id": state_dict["domain_id"],
                "versions": state_dict["versions"],
                "domain_info": state_dict.get(
                    "domain_info", self._get_domain_info(state_dict["domain_id"])
                ),
                "file_info": state_dict.get(
                    "file_info", self._get_files_info(state_dict["domain_id"])
                ),
                "db": self.db,
            }

            result = await self.graph.ainvoke(state)
            llm_content = result["messages"][-1].content

            # Debug log to see raw LLM response
            logger.debug(f"Raw LLM response: {llm_content}")
            # print(f"Raw LLM response: {llm_content}")

            try:
                # Clean the response string if needed
                cleaned_content = llm_content.strip()
                # Handle cases where response starts with { but isn't valid JSON
                if cleaned_content.startswith("{") and cleaned_content.endswith("}"):
                    llm_response = json.loads(cleaned_content)
                else:
                    # Wrap non-JSON responses in a proper structure
                    llm_response = {
                        "message": cleaned_content,
                        "visualization": {"type": "none", "content": "", "title": ""},
                    }

                # Validate response structure
                if not isinstance(llm_response, dict):
                    raise ValueError("Response is not a dictionary")
                if "message" not in llm_response:
                    raise ValueError("Response missing 'message' field")
                if "visualization" not in llm_response:
                    raise ValueError("Response missing 'visualization' field")

                response = {
                    "message_type": "TEXT",
                    "intent": "ANALYZE_RESULTS",
                    "response": llm_response["message"],
                    "suggestions": [],
                    "warnings": [],
                }

                # Add visualization if present and valid
                viz_data = llm_response.get("visualization", {})
                if viz_data and viz_data.get("type") != "none":
                    if not all(k in viz_data for k in ["type", "content", "title"]):
                        logger.warning("Incomplete visualization data structure")
                    else:
                        response["visualization"] = viz_data
                        logger.info(f"Added visualization: {viz_data['type']}")

                return response

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}\nContent: {llm_content}")
                return {
                    "message_type": "TEXT",
                    "intent": "ANALYZE_RESULTS",
                    "response": llm_content,  # Fallback to raw response
                    "warnings": ["Failed to parse structured response format"],
                }
            except ValueError as e:
                logger.error(f"Validation error: {str(e)}")
                return {
                    "message_type": "TEXT",
                    "intent": "ANALYZE_RESULTS",
                    "response": llm_content,  # Fallback to raw response
                    "warnings": [f"Invalid response structure: {str(e)}"],
                }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "message_type": "ERROR",
                "intent": "ERROR",
                "response": f"Error processing message: {str(e)}",
                "warnings": [str(e)],
            }
