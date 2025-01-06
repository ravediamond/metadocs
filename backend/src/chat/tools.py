import json
from typing import Optional, Dict, Any
from uuid import UUID
from langchain_core.tools import BaseTool
from ..models.models import (
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
)


def get_version_output(version_obj: Any) -> Optional[Dict]:
    """Helper to load version output data"""
    if not version_obj or not version_obj.output_path:
        return None
    try:
        with open(version_obj.output_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading version output: {str(e)}")
        return None


def get_markdown_output(version_obj: Any) -> Optional[str]:
    """Helper to load markdown output data"""
    if not version_obj or not version_obj.output_path:
        return None
    try:
        with open(version_obj.output_path, "r") as f:
            return f.read()  # Read as plain text
    except Exception as e:
        print(f"Error reading markdown output: {str(e)}")
        return None


def create_data_loading_tools(db):
    """Create tools for loading different types of version data"""

    class ParseDataTool(BaseTool):
        name: str = "load_parse_data"
        description: str = "Load parsed markdown data from a specific version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(ParseVersion).filter_by(version_id=version_id).first()
            if not version:
                return None

            return {
                "data": get_markdown_output(version),  # Use the new helper function
                "file_version_id": version.input_file_version_id,
                "status": version.status,
                "errors": version.errors,
            }

    class ExtractDataTool(BaseTool):
        name: str = "load_extract_data"
        description: str = "Load extracted entities from a specific version"
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

    class MergeDataTool(BaseTool):
        name: str = "load_merge_data"
        description: str = "Load merged data from a specific version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(MergeVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_version_output(version),
                "extract_version_ids": version.input_extract_version_ids,
                "status": version.status,
                "error": version.error,
            }

    class GroupDataTool(BaseTool):
        name: str = "load_group_data"
        description: str = "Load entity group data from a specific version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(GroupVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_version_output(version),
                "merge_version_id": version.input_merge_version_id,
                "status": version.status,
                "error": version.error,
            }

    class OntologyDataTool(BaseTool):
        name: str = "load_ontology_data"
        description: str = "Load ontology data from a specific version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(OntologyVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_version_output(version),
                "merge_version_id": version.input_merge_version_id,
                "group_version_id": version.input_group_version_id,
                "status": version.status,
                "error": version.error,
            }

    class VisualizationTool(BaseTool):
        name: str = "generate_visualization"
        description: str = "Generate visualization based on content type"
        return_direct: bool = True

        def _run(self, content_type: str, data: Dict) -> Optional[dict]:
            """Generate visualization based on content type and data"""
            try:
                if content_type == "mermaid":
                    # Generate mermaid diagram
                    return {
                        "type": "mermaid",
                        "content": data.get("diagram", ""),
                        "title": data.get("title", "Diagram"),
                    }
                elif content_type == "code":
                    # Generate code visualization
                    return {
                        "type": "code",
                        "content": data.get("code", ""),
                        "language": data.get("language", "python"),
                        "title": data.get("title", "Code"),
                    }
                elif content_type == "markdown":
                    # Generate markdown content
                    return {
                        "type": "markdown",
                        "content": data.get("content", ""),
                        "title": data.get("title", "Documentation"),
                    }
            except Exception as e:
                print(f"Error generating visualization: {str(e)}")
                return None

    return [
        ParseDataTool(),
        ExtractDataTool(),
        MergeDataTool(),
        GroupDataTool(),
        OntologyDataTool(),
        VisualizationTool(),
    ]
