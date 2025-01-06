import logging
import json
from datetime import datetime
from typing import TypedDict, List, Any, Dict, Annotated, Optional
from uuid import UUID
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from .tools import create_data_loading_tools, create_processing_tools
from .prompts import CHAT_PROMPT
from ..models.models import (
    Domain,
    DomainVersionFile,
    FileVersion,
    File,
    ProcessingPipeline,
    PipelineStatus,
    PipelineStage,
    ParseVersion,
    ExtractVersion,
    GraphVersion,
)
from ..processors.parse_processor import ParseProcessor
from ..processors.extract_processor import ExtractProcessor
from ..processors.graph_processor import GraphProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tenant_id: UUID
    domain_id: UUID
    domain_info: Dict[str, Any]
    file_info: Dict[str, Any]
    pipeline: Dict[str, Any]
    db: Any


class GraphAssistant:
    def __init__(self, llm_client, db, config):
        self.llm = llm_client.bind_tools(
            [*create_data_loading_tools(db), *create_processing_tools(db, config)]
        )
        self.db = db
        self.config = config
        self.graph = self._create_graph()

    def _get_domain_info(self, domain_id: UUID) -> dict:
        """Get domain information"""
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
        """Get information about domain files"""
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
                "processed": self._check_file_processed(file_version.file_version_id),
            }
            for domain_version_file, file_version, file in files
        }

    def _check_file_processed(self, file_version_id: UUID) -> bool:
        """Check if a file has been processed"""
        parse_version = (
            self.db.query(ParseVersion)
            .filter(ParseVersion.input_file_version_id == file_version_id)
            .first()
        )
        return parse_version is not None and parse_version.status == "completed"

    def _get_pipeline_context(self, domain_id: UUID) -> dict:
        """Get current pipeline status and context"""
        pipeline = (
            self.db.query(ProcessingPipeline)
            .filter(ProcessingPipeline.domain_id == domain_id)
            .order_by(ProcessingPipeline.created_at.desc())
            .first()
        )

        if not pipeline:
            return {
                "has_pipeline": False,
                "message": "No processing pipeline found. I can start one for you.",
                "unprocessed_files": self._get_unprocessed_files_count(domain_id),
            }

        # Get latest versions
        latest_versions = {
            "parse": pipeline.get_latest_version_by_stage(PipelineStage.PARSE),
            "extract": pipeline.get_latest_version_by_stage(PipelineStage.EXTRACT),
            "graph": pipeline.get_latest_version_by_stage(PipelineStage.GRAPH),
        }

        # Get processing results if available
        results = {}
        for stage, version_id in latest_versions.items():
            if version_id:
                results[stage] = self._get_stage_results(stage, version_id)

        return {
            "has_pipeline": True,
            "pipeline_id": pipeline.pipeline_id,
            "status": pipeline.status,
            "stage": pipeline.stage,
            "error": pipeline.error,
            "versions": latest_versions,
            "results": results,
            "can_continue": pipeline.status != PipelineStatus.FAILED,
            "needs_attention": pipeline.status == PipelineStatus.FAILED
            or bool(pipeline.error),
        }

    def _get_unprocessed_files_count(self, domain_id: UUID) -> int:
        """Get count of unprocessed files"""
        files = self._get_files_info(domain_id)
        return sum(1 for f in files.values() if not f["processed"])

    def _get_stage_results(self, stage: str, version_id: UUID) -> Optional[Dict]:
        """Get processing results for a stage"""
        version_models = {
            "parse": ParseVersion,
            "extract": ExtractVersion,
            "graph": GraphVersion,
        }

        version = (
            self.db.query(version_models[stage])
            .filter_by(version_id=version_id)
            .first()
        )

        if not version or not version.output_path:
            return None

        try:
            with open(version.output_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {stage} results: {e}")
            return None

    def _create_graph(self):
        """Create the processing graph"""
        builder = StateGraph(State)

        # Chatbot node - processes initial message and pipeline management
        def chatbot(state: State):
            # Prepare prompt inputs
            prompt_inputs = {
                "messages": state["messages"],
                "domain_info": state["domain_info"],
                "file_info": state["file_info"],
                "pipeline": state["pipeline"],
            }

            messages = CHAT_PROMPT.format_messages(**prompt_inputs)
            response = self.llm.invoke(messages)
            return {"messages": [response]}

        # Tools node - handles data operations and processing
        tool_node = ToolNode(
            tools=[
                *create_data_loading_tools(self.db),
                *create_processing_tools(self.db, self.config),
            ]
        )

        # Add nodes
        builder.add_node("chatbot", chatbot)
        builder.add_node("tools", tool_node)

        # Router function
        def route(state: State):
            if messages := state.get("messages", []):
                last_msg = messages[-1]
                if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
                    return "tools"
            return "__end__"

        # Add edges
        builder.add_conditional_edges(
            "chatbot", route, {"tools": "tools", "__end__": "__end__"}
        )
        builder.add_edge("tools", "chatbot")

        builder.set_entry_point("chatbot")
        return builder.compile()

    async def process_message(self, state_dict):
        """Process a message and handle pipeline operations"""
        try:
            # Prepare state with pipeline context
            state = {
                "messages": state_dict["messages"],
                "tenant_id": state_dict["tenant_id"],
                "domain_id": state_dict["domain_id"],
                "domain_info": state_dict.get(
                    "domain_info", self._get_domain_info(state_dict["domain_id"])
                ),
                "file_info": state_dict.get(
                    "file_info", self._get_files_info(state_dict["domain_id"])
                ),
                "pipeline": self._get_pipeline_context(state_dict["domain_id"]),
                "db": self.db,
            }

            # Process through graph
            result = await self.graph.ainvoke(state)

            # Get final message
            llm_response = result["messages"][-1]

            # Debug log
            logger.debug(f"Raw LLM response: {llm_response.content}")

            try:
                # Parse response
                return self._format_response(llm_response.content)
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error: {str(e)}\nContent: {llm_response.content}"
                )
                return self._format_error_response(
                    "Failed to parse response format", llm_response.content
                )
            except ValueError as e:
                logger.error(f"Validation error: {str(e)}")
                return self._format_error_response(
                    f"Invalid response structure: {str(e)}", llm_response.content
                )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return self._format_error_response(
                f"Error processing message: {str(e)}", None
            )

    def _format_response(self, content: str) -> dict:
        """Format the LLM response into a structured format"""
        # Clean the response string
        cleaned_content = content.strip()

        # Handle JSON responses
        if cleaned_content.startswith("{") and cleaned_content.endswith("}"):
            response_data = json.loads(cleaned_content)

            # Validate response structure
            if not isinstance(response_data, dict):
                raise ValueError("Response is not a dictionary")
            if "message" not in response_data:
                raise ValueError("Response missing 'message' field")

            # Build response
            formatted_response = {
                "message_type": response_data.get("message_type", "TEXT"),
                "intent": response_data.get("intent", "CHAT"),
                "response": response_data["message"],
                "suggestions": response_data.get("suggestions", []),
                "warnings": response_data.get("warnings", []),
            }

            # Add visualization if present
            viz_data = response_data.get("visualization", {})
            if viz_data and viz_data.get("type") != "none":
                if not all(k in viz_data for k in ["type", "content", "title"]):
                    logger.warning("Incomplete visualization data structure")
                else:
                    formatted_response["visualization"] = viz_data
                    logger.info(f"Added visualization: {viz_data['type']}")

            # Add pipeline info if present
            pipeline_data = response_data.get("pipeline", {})
            if pipeline_data:
                formatted_response["pipeline"] = pipeline_data

            return formatted_response

        # Handle non-JSON responses
        return {
            "message_type": "TEXT",
            "intent": "CHAT",
            "response": cleaned_content,
            "suggestions": [],
            "warnings": ["Response was not in structured format"],
        }

    def _format_error_response(
        self, error_message: str, raw_content: Optional[str]
    ) -> dict:
        """Format an error response"""
        return {
            "message_type": "ERROR",
            "intent": "ERROR",
            "response": error_message,
            "warnings": [error_message],
            "raw_content": raw_content,
        }

    async def update_graph(self, domain_id: UUID, feedback: str) -> dict:
        """Handle feedback to update the knowledge graph"""
        try:
            # Get current pipeline context
            pipeline_context = self._get_pipeline_context(domain_id)

            if not pipeline_context["has_pipeline"]:
                return {
                    "success": False,
                    "message": "No pipeline found to update",
                    "error": "Pipeline not found",
                }

            # Get latest graph version
            graph_version_id = pipeline_context["versions"].get("graph")
            if not graph_version_id:
                return {
                    "success": False,
                    "message": "No graph version found to update",
                    "error": "Graph version not found",
                }

            # Get graph version
            graph_version = (
                self.db.query(GraphVersion)
                .filter_by(version_id=graph_version_id)
                .first()
            )

            # Create graph processor
            graph_processor = GraphProcessor(
                extract_versions=[],  # Will use existing graph data
                graph_version=graph_version,
                config_manager=self.config,
            )

            # Process feedback
            result = await graph_processor.process_feedback(feedback)

            if result.success:
                return {
                    "success": True,
                    "message": "Graph updated successfully",
                    "data": result.data,
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update graph",
                    "error": result.error,
                }

        except Exception as e:
            logger.error(f"Error updating graph: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "Error updating graph",
                "error": str(e),
            }
