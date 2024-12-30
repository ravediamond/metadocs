from typing import Dict, Any, List, Optional
from uuid import UUID
import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.models import (
    ProcessingPipeline,
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
    Domain,
    DomainVersion,
)
from ..core.database import get_db

logger = logging.getLogger(__name__)


def get_version_output(version_obj) -> Dict[str, Any]:
    """Helper to load version output data"""
    try:
        if not version_obj.output_path or not Path(version_obj.output_path).exists():
            return None

        with open(version_obj.output_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading version output: {str(e)}")
        return None


def load_parsed_data(
    tenant_id: UUID, domain_id: UUID, parse_version_id: UUID, db: Session
) -> Dict[str, Any]:
    """Load parsed data for a specific version"""
    try:
        parse_version = (
            db.query(ParseVersion)
            .filter(ParseVersion.version_id == parse_version_id)
            .first()
        )

        if not parse_version:
            logger.error(f"Parse version {parse_version_id} not found")
            return None

        return get_version_output(parse_version)

    except Exception as e:
        logger.error(f"Error loading parsed data: {str(e)}", exc_info=True)
        raise


def load_entities(
    tenant_id: UUID, domain_id: UUID, extract_version_id: UUID, db: Session
) -> Dict[str, Any]:
    """Load extracted entities for a specific version"""
    try:
        extract_version = (
            db.query(ExtractVersion)
            .filter(ExtractVersion.version_id == extract_version_id)
            .first()
        )

        if not extract_version:
            logger.error(f"Extract version {extract_version_id} not found")
            return None

        return get_version_output(extract_version)

    except Exception as e:
        logger.error(f"Error loading entities: {str(e)}", exc_info=True)
        raise


def load_merge_results(
    tenant_id: UUID, domain_id: UUID, merge_version_id: UUID, db: Session
) -> Dict[str, Any]:
    """Load merged entities for a specific version"""
    try:
        merge_version = (
            db.query(MergeVersion)
            .filter(MergeVersion.version_id == merge_version_id)
            .first()
        )

        if not merge_version:
            logger.error(f"Merge version {merge_version_id} not found")
            return None

        return get_version_output(merge_version)

    except Exception as e:
        logger.error(f"Error loading merge results: {str(e)}", exc_info=True)
        raise


def load_groups(
    tenant_id: UUID, domain_id: UUID, group_version_id: UUID, db: Session
) -> Dict[str, Any]:
    """Load entity groups for a specific version"""
    try:
        group_version = (
            db.query(GroupVersion)
            .filter(GroupVersion.version_id == group_version_id)
            .first()
        )

        if not group_version:
            logger.error(f"Group version {group_version_id} not found")
            return None

        return get_version_output(group_version)

    except Exception as e:
        logger.error(f"Error loading groups: {str(e)}", exc_info=True)
        raise


def load_ontology(
    tenant_id: UUID, domain_id: UUID, ontology_version_id: UUID, db: Session
) -> Dict[str, Any]:
    """Load ontology for a specific version"""
    try:
        ontology_version = (
            db.query(OntologyVersion)
            .filter(OntologyVersion.version_id == ontology_version_id)
            .first()
        )

        if not ontology_version:
            logger.error(f"Ontology version {ontology_version_id} not found")
            return None

        return get_version_output(ontology_version)

    except Exception as e:
        logger.error(f"Error loading ontology: {str(e)}", exc_info=True)
        raise


def update_todo_list(
    tenant_id: UUID, domain_id: UUID, todo_item: Dict[str, Any], db: Session
) -> bool:
    """Update the todo list for a domain"""
    try:
        # Here you would implement your todo list storage logic
        # Could be in a database table or a file
        logger.info(f"Adding todo item for domain {domain_id}")
        return True

    except Exception as e:
        logger.error(f"Error updating todo list: {str(e)}", exc_info=True)
        raise
