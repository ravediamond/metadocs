from typing import Optional
from uuid import UUID
import json
from langchain_core.tools import BaseTool
from ..models.models import (
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
    Domain,
    DomainVersionFile,
)


def get_version_output(version_obj):
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

    class DomainInfoTool(BaseTool):
        name: str = "get_domain_info"
        description: str = "Get information about the current domain"
        return_direct: bool = True

        def _run(self, domain_id: UUID) -> Optional[dict]:
            domain = db.query(Domain).filter_by(domain_id=domain_id).first()
            if not domain:
                return None
            return {
                "name": domain.name,
                "description": domain.description,
                "created_at": domain.created_at,
                "updated_at": domain.updated_at,
            }

    class FileInfoTool(BaseTool):
        name: str = "get_file_info"
        description: str = "Get information about files in the domain"
        return_direct: bool = True

        def _run(self, domain_id: UUID) -> Optional[dict]:
            files = db.query(DomainVersionFile).filter_by(domain_id=domain_id).all()
            if not files:
                return None
            return {
                file.file_id: {
                    "name": file.name,
                    "description": file.description,
                    "file_type": file.file_type,
                    "created_at": file.created_at,
                }
                for file in files
            }

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
                "description": version.description,
                "file_version_id": version.file_version_id,
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
                "description": version.description,
                "parse_version_id": version.parse_version_id,
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
                "description": version.description,
                "extract_version_ids": version.extract_version_ids,
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
                "description": version.description,
                "merge_version_id": version.merge_version_id,
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
                "description": version.description,
                "merge_version_id": version.merge_version_id,
                "group_version_id": version.group_version_id,
            }

    return [
        DomainInfoTool(),
        FileInfoTool(),
        ParseDataTool(),
        ExtractDataTool(),
        MergeDataTool(),
        GroupDataTool(),
        OntologyDataTool(),
    ]
