# process.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Optional
import logging

from ..models.models import (
    Domain,
    File as FileModel,
    ProcessingPipeline,
    ParseVersion,
    ExtractVersion,
    MergeVersion,
    GroupVersion,
    OntologyVersion,
    GraphVersion,
)
from ..models.schemas import ProcessingStatus, FileStatus
from ..core.database import get_db
from ..processors.pdf.processor import PDFProcessor
from ..processors.entity.processor import EntityProcessor
from ..processors.groups.processor import GroupProcessor
from ..processors.ontology.processor import OntologyProcessor
from ..processors.merger.processor import EntityMerger
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


class VersionManager:
    def __init__(self, pipeline_id: UUID, db: Session):
        self.pipeline_id = pipeline_id
        self.db = db

    def _get_next_version(self, version_class) -> int:
        latest = (
            self.db.query(version_class)
            .filter(version_class.pipeline_id == self.pipeline_id)
            .order_by(version_class.version_number.desc())
            .first()
        )
        return (latest.version_number + 1) if latest else 1

    def create_parse_version(self, input_path: str) -> ParseVersion:
        version = ParseVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(ParseVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_extract_version(self, input_path: str) -> ExtractVersion:
        version = ExtractVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(ExtractVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_merge_version(self, input_paths: List[str]) -> MergeVersion:
        version = MergeVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(MergeVersion),
            input_path=",".join(input_paths),
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_group_version(self, input_path: str) -> GroupVersion:
        version = GroupVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(GroupVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_ontology_version(self, input_path: str) -> OntologyVersion:
        version = OntologyVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(OntologyVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version

    def create_graph_version(self, input_path: str) -> GraphVersion:
        version = GraphVersion(
            pipeline_id=self.pipeline_id,
            version_number=self._get_next_version(GraphVersion),
            input_path=input_path,
            status="processing",
        )
        self.db.add(version)
        self.db.commit()
        return version


async def process_file(
    file: FileModel, pipeline: ProcessingPipeline, config: ConfigManager, db: Session
) -> bool:
    """Process a single file through PDF and Entity extraction stages with versioning"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        # PDF Processing Version
        parse_version = version_manager.create_parse_version(file.filepath)
        pipeline.current_parse_id = parse_version.version_id
        db.commit()

        # PDF Processing
        pdf_processor = PDFProcessor(file, config)
        pdf_result = pdf_processor.process()

        if not pdf_result.success:
            parse_version.status = "failed"
            parse_version.error = f"PDF processing failed: {pdf_result.message}"
            file.processing_status = "failed"
            file.processing_error = parse_version.error
            db.commit()
            return False

        parse_version.output_path = pdf_result.markdown_path
        parse_version.status = "completed"
        file.markdown_path = pdf_result.markdown_path
        db.commit()

        # Entity Processing Version
        extract_version = version_manager.create_extract_version(
            pdf_result.markdown_path
        )
        pipeline.current_extract_id = extract_version.version_id
        db.commit()

        # Entity Processing
        entity_processor = EntityProcessor(file, config)
        entity_result = entity_processor.process()

        if not entity_result.success:
            extract_version.status = "failed"
            extract_version.error = f"Entity extraction failed: {entity_result.message}"
            file.processing_status = "failed"
            file.processing_error = extract_version.error
            db.commit()
            return False

        extract_version.output_path = entity_result.analysis_path
        extract_version.status = "completed"
        file.entity_extraction_path = entity_result.analysis_path
        file.processing_status = "completed"
        file.last_processed_at = datetime.utcnow()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error processing file {file.file_id}: {str(e)}")
        file.processing_status = "failed"
        file.processing_error = str(e)

        # Update current version if exists
        current_version = None
        if pipeline.current_parse_id and not parse_version.status == "completed":
            current_version = parse_version
        elif pipeline.current_extract_id and not extract_version.status == "completed":
            current_version = extract_version

        if current_version:
            current_version.status = "failed"
            current_version.error = str(e)

        db.commit()
        return False


async def process_domain(
    domain_id: UUID,
    pipeline: ProcessingPipeline,
    files: List[FileModel],
    config: ConfigManager,
    db: Session,
):
    """Process domain-level analysis with versioning"""
    version_manager = VersionManager(pipeline.pipeline_id, db)

    try:
        # Get all successful entity extraction paths
        entity_paths = [
            f.entity_extraction_path
            for f in files
            if f.processing_status == "completed" and f.entity_extraction_path
        ]

        # Merge entities
        merge_version = version_manager.create_merge_version(entity_paths)
        pipeline.current_merge_id = merge_version.version_id
        db.commit()

        merger = EntityMerger(pipeline, config)
        merge_result = merger.process()

        if not merge_result.success:
            merge_version.status = "failed"
            merge_version.error = f"Entity merging failed: {merge_result.message}"
            pipeline.status = "failed"
            pipeline.error = merge_version.error
            db.commit()
            return

        merge_version.output_path = merge_result.merged_path
        merge_version.status = "completed"
        db.commit()

        # Process groups
        group_version = version_manager.create_group_version(merge_result.merged_path)
        pipeline.current_group_id = group_version.version_id
        db.commit()

        group_processor = GroupProcessor(pipeline, config)
        group_result = group_processor.process()

        if not group_result.success:
            group_version.status = "failed"
            group_version.error = f"Group analysis failed: {group_result.message}"
            pipeline.status = "failed"
            pipeline.error = group_version.error
            db.commit()
            return

        group_version.output_path = group_result.groups_path
        group_version.status = "completed"
        db.commit()

        # Generate ontology
        ontology_version = version_manager.create_ontology_version(
            group_result.groups_path
        )
        pipeline.current_ontology_id = ontology_version.version_id
        db.commit()

        ontology_processor = OntologyProcessor(pipeline, config)
        ontology_result = ontology_processor.process()

        if not ontology_result.success:
            ontology_version.status = "failed"
            ontology_version.error = (
                f"Ontology generation failed: {ontology_result.message}"
            )
            pipeline.status = "failed"
            pipeline.error = ontology_version.error
            db.commit()
            return

        ontology_version.output_path = ontology_result.diagram_path
        ontology_version.status = "completed"
        db.commit()

        # Mark pipeline as completed
        pipeline.status = "completed"
        db.commit()

    except Exception as e:
        logger.error(f"Error in domain processing for {domain_id}: {str(e)}")
        pipeline.status = "failed"
        pipeline.error = str(e)

        # Update current version if exists
        current_version = None
        if pipeline.current_merge_id:
            current_version = db.query(MergeVersion).get(pipeline.current_merge_id)
        elif pipeline.current_group_id:
            current_version = db.query(GroupVersion).get(pipeline.current_group_id)
        elif pipeline.current_ontology_id:
            current_version = db.query(OntologyVersion).get(
                pipeline.current_ontology_id
            )

        if current_version and current_version.status == "processing":
            current_version.status = "failed"
            current_version.error = str(e)

        db.commit()


async def process_all(domain_id: UUID, db: Session):
    """Main processing coordinator with versioning"""
    try:
        # Get domain info and setup config
        domain = db.query(Domain).filter(Domain.domain_id == domain_id).first()
        config = ConfigManager(db, str(domain.tenant_id), str(domain.domain_id))

        # Create new processing pipeline
        pipeline = ProcessingPipeline(domain_id=domain_id, status="processing")
        db.add(pipeline)
        db.commit()

        # Get all files for processing
        files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

        # Process all files first
        success = True
        for file in files:
            file_success = await process_file(file, pipeline, config, db)
            success = success and file_success

        # If all files processed successfully, start domain processing
        if success:
            await process_domain(domain_id, pipeline, files, config, db)

    finally:
        db.close()
