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


def create_data_loading_tools(db):
    """Create tools for loading different types of version data"""

    class ParseDataTool(BaseTool):
        name: str = "load_parse_data"
        description: str = "Load parsed data from a specific version"
        return_direct: bool = True

        def _run(self, version_id: UUID) -> Optional[dict]:
            version = db.query(ParseVersion).filter_by(version_id=version_id).first()
            if not version:
                return None
            return {
                "data": get_version_output(version),
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

    return [
        ParseDataTool(),
        ExtractDataTool(),
        MergeDataTool(),
        GroupDataTool(),
        OntologyDataTool(),
    ]
