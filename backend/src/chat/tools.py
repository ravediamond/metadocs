from typing import Dict, List, Optional, Any
from uuid import UUID
import json
import logging
from langchain_core.tools import BaseTool
from ..models.models import (
    ParseVersion,
    ExtractVersion,
    GraphVersion,
    ProcessingPipeline,
    PipelineStatus,
    PipelineStage,
    FileVersion,
    Domain,
    DomainVersion,
)
from ..processors.parse_processor import ParseProcessor
from ..processors.extract_processor import ExtractProcessor
from ..processors.graph_processor import GraphProcessor

logger = logging.getLogger(__name__)


def get_version_output(version_obj: Any) -> Optional[Dict]:
    """Helper to load version output data"""
    if not version_obj or not version_obj.output_path:
        return None
    try:
        with open(version_obj.output_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading version output: {str(e)}")
        return None


def get_markdown_output(version_obj: Any) -> Optional[str]:
    """Helper to load markdown output data"""
    if not version_obj or not version_obj.output_path:
        return None
    try:
        with open(version_obj.output_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading markdown output: {str(e)}")
        return None


def create_data_loading_tools(db):
    """Create tools for loading different types of data"""

    class LoadParseData(BaseTool):
        name: str = "load_parse_data"
        description: str = "Load parsed markdown data from a specific version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(ParseVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_markdown_output(version),
                "file_version_id": version.input_file_version_id,
                "status": version.status,
                "errors": version.errors,
            }

    class LoadExtractData(BaseTool):
        name: str = "load_extract_data"
        description: str = "Load extracted entities from a version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(ExtractVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_version_output(version),
                "parse_version_id": version.input_parse_version_id,
                "status": version.status,
                "errors": version.errors,
            }

    class LoadGraphData(BaseTool):
        name: str = "load_graph_data"
        description: str = (
            "Load graph data including entities, relationships, and visualization"
        )
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(GraphVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_version_output(version),
                "extract_version_ids": version.input_extract_version_ids,
                "status": version.status,
                "error": version.error,
            }

    return [LoadParseData(), LoadExtractData(), LoadGraphData()]


def create_processing_tools(db, config):
    """Create tools for managing processing pipeline"""

    class CreatePipeline(BaseTool):
        name: str = "create_pipeline"
        description: str = "Create a new processing pipeline for a domain"
        return_direct: bool = True

        def _run(self, domain_id: UUID) -> Dict:
            try:
                pipeline = ProcessingPipeline(
                    domain_id=domain_id,
                    stage=PipelineStage.NOT_STARTED,
                    status=PipelineStatus.UNINITIALIZED,
                )
                db.add(pipeline)
                db.commit()
                return {
                    "success": True,
                    "pipeline_id": pipeline.pipeline_id,
                    "message": "Pipeline created successfully",
                }
            except Exception as e:
                logger.error(f"Error creating pipeline: {e}")
                return {"success": False, "error": str(e)}

    class ProcessFile(BaseTool):
        name: str = "process_file"
        description: str = "Process a specific file through parsing and extraction"
        return_direct: bool = True

        def _run(self, pipeline_id: UUID, file_version_id: UUID) -> Dict:
            try:
                pipeline = db.query(ProcessingPipeline).get(pipeline_id)
                if not pipeline:
                    return {"success": False, "error": "Pipeline not found"}

                file_version = db.query(FileVersion).get(file_version_id)
                if not file_version:
                    return {"success": False, "error": "File version not found"}

                # Create parse version
                parse_version = ParseVersion(
                    pipeline_id=pipeline_id,
                    version_number=len(pipeline.parse_versions) + 1,
                    input_file_version_id=file_version_id,
                    status="processing",
                )
                db.add(parse_version)
                db.commit()

                # Start parsing
                parse_processor = ParseProcessor(file_version, parse_version, config)
                parse_result = parse_processor.process()

                if not parse_result.success:
                    return {
                        "success": False,
                        "stage": "parse",
                        "error": parse_result.error,
                    }

                # Create extract version
                extract_version = ExtractVersion(
                    pipeline_id=pipeline_id,
                    version_number=len(pipeline.extract_versions) + 1,
                    input_parse_version_id=parse_version.version_id,
                    status="processing",
                )
                db.add(extract_version)
                db.commit()

                # Start extraction
                extract_processor = ExtractProcessor(
                    parse_version, extract_version, config
                )
                extract_result = extract_processor.process()

                return {
                    "success": extract_result.success,
                    "parse_version_id": parse_version.version_id,
                    "extract_version_id": extract_version.version_id,
                    "error": (
                        extract_result.error if not extract_result.success else None
                    ),
                }

            except Exception as e:
                logger.error(f"Error processing file: {e}")
                return {"success": False, "error": str(e)}

    class CreateGraph(BaseTool):
        name: str = "create_graph"
        description: str = "Create or update knowledge graph from extracted data"
        return_direct: bool = True

        def _run(self, pipeline_id: UUID, extract_version_ids: List[UUID]) -> Dict:
            try:
                pipeline = db.query(ProcessingPipeline).get(pipeline_id)
                if not pipeline:
                    return {"success": False, "error": "Pipeline not found"}

                extract_versions = (
                    db.query(ExtractVersion)
                    .filter(ExtractVersion.version_id.in_(extract_version_ids))
                    .all()
                )

                # Create graph version
                graph_version = GraphVersion(
                    pipeline_id=pipeline_id,
                    version_number=len(pipeline.graph_versions) + 1,
                    input_extract_version_ids=extract_version_ids,
                    status="processing",
                )
                db.add(graph_version)
                db.commit()

                # Process graph
                graph_processor = GraphProcessor(
                    extract_versions, graph_version, config
                )
                graph_result = graph_processor.process()

                return {
                    "success": graph_result.success,
                    "graph_version_id": graph_version.version_id,
                    "error": graph_result.error if not graph_result.success else None,
                    "visualization": (
                        graph_result.data.get("visualization")
                        if graph_result.success
                        else None
                    ),
                }

            except Exception as e:
                logger.error(f"Error creating graph: {e}")
                return {"success": False, "error": str(e)}

    class UpdateGraphWithFeedback(BaseTool):
        name: str = "update_graph"
        description: str = "Update existing knowledge graph based on feedback"
        return_direct: bool = True

        def _run(self, graph_version_id: UUID, feedback: str) -> Dict:
            try:
                graph_version = db.query(GraphVersion).get(graph_version_id)
                if not graph_version:
                    return {"success": False, "error": "Graph version not found"}

                extract_versions = (
                    db.query(ExtractVersion)
                    .filter(
                        ExtractVersion.version_id.in_(
                            graph_version.input_extract_version_ids
                        )
                    )
                    .all()
                )

                graph_processor = GraphProcessor(
                    extract_versions, graph_version, config
                )
                update_result = graph_processor.update_graph(feedback)

                return {
                    "success": update_result.success,
                    "updated_graph_version_id": graph_version.version_id,
                    "error": update_result.error if not update_result.success else None,
                    "visualization": (
                        update_result.data.get("visualization")
                        if update_result.success
                        else None
                    ),
                }

            except Exception as e:
                logger.error(f"Error updating graph: {e}")
                return {"success": False, "error": str(e)}

    class CheckPipelineStatus(BaseTool):
        name: str = "check_pipeline_status"
        description: str = "Check the status of a processing pipeline"
        return_direct: bool = True

        def _run(self, pipeline_id: UUID) -> Dict:
            try:
                pipeline = db.query(ProcessingPipeline).get(pipeline_id)
                if not pipeline:
                    return {"success": False, "error": "Pipeline not found"}

                # Get latest versions
                latest_parse = (
                    db.query(ParseVersion)
                    .filter_by(pipeline_id=pipeline_id)
                    .order_by(ParseVersion.version_number.desc())
                    .first()
                )

                latest_extract = (
                    db.query(ExtractVersion)
                    .filter_by(pipeline_id=pipeline_id)
                    .order_by(ExtractVersion.version_number.desc())
                    .first()
                )

                latest_graph = (
                    db.query(GraphVersion)
                    .filter_by(pipeline_id=pipeline_id)
                    .order_by(GraphVersion.version_number.desc())
                    .first()
                )

                return {
                    "success": True,
                    "status": pipeline.status,
                    "stage": pipeline.stage,
                    "error": pipeline.error,
                    "versions": {
                        "parse": {
                            "id": latest_parse.version_id if latest_parse else None,
                            "status": latest_parse.status if latest_parse else None,
                        },
                        "extract": {
                            "id": latest_extract.version_id if latest_extract else None,
                            "status": latest_extract.status if latest_extract else None,
                        },
                        "graph": {
                            "id": latest_graph.version_id if latest_graph else None,
                            "status": latest_graph.status if latest_graph else None,
                        },
                    },
                }

            except Exception as e:
                logger.error(f"Error checking pipeline status: {e}")
                return {"success": False, "error": str(e)}

    class GenerateVisualization(BaseTool):
        name: str = "generate_visualization"
        description: str = "Generate visualization for specific data"
        return_direct: bool = True

        def _run(self, data: Dict, viz_type: str = "mermaid") -> Dict:
            try:
                if viz_type == "mermaid":
                    # Generate mermaid diagram from graph data
                    return {
                        "success": True,
                        "visualization": {
                            "type": "mermaid",
                            "content": self._generate_mermaid(data),
                            "title": "Knowledge Graph Visualization",
                        },
                    }
                elif viz_type == "markdown":
                    # Generate markdown representation
                    return {
                        "success": True,
                        "visualization": {
                            "type": "markdown",
                            "content": self._generate_markdown(data),
                            "title": "Data Summary",
                        },
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported visualization type: {viz_type}",
                    }

            except Exception as e:
                logger.error(f"Error generating visualization: {e}")
                return {"success": False, "error": str(e)}

        def _generate_mermaid(self, data: Dict) -> str:
            # Convert graph data to mermaid syntax
            mermaid = ["graph TD"]

            # Add nodes
            for entity in data.get("entities", []):
                mermaid.append(f'    {entity["id"]}["{entity["name"]}"]')

            # Add relationships
            for rel in data.get("relationships", []):
                mermaid.append(
                    f'    {rel["source"]} --> |"{rel["type"]}"|{rel["target"]}'
                )

            return "\n".join(mermaid)

        def _generate_markdown(self, data: Dict) -> str:
            # Convert data to markdown format
            sections = ["# Data Summary\n"]

            if "entities" in data:
                sections.append("## Entities\n")
                for entity in data["entities"]:
                    sections.append(f"### {entity['name']}\n")
                    if "properties" in entity:
                        for key, value in entity["properties"].items():
                            sections.append(f"- {key}: {value}\n")

            if "relationships" in data:
                sections.append("\n## Relationships\n")
                for rel in data["relationships"]:
                    sections.append(
                        f"- {rel['source']} {rel['type']} {rel['target']}\n"
                    )

            return "\n".join(sections)

    return [
        CreatePipeline(),
        ProcessFile(),
        CreateGraph(),
        UpdateGraphWithFeedback(),
        CheckPipelineStatus(),
        GenerateVisualization(),
    ]
