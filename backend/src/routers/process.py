from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Dict
import logging

from ..models.models import Domain, File as FileModel, DomainProcessing
from ..models.schemas import ProcessingStatus, FileStatus, DomainProcessingSchema
from ..core.database import get_db
from ..processors.pdf.processor import PDFProcessor
from ..processors.entity.processor import EntityProcessor
from ..processors.groups.processor import GroupProcessor
from ..processors.ontology.processor import OntologyProcessor
from ..processors.merger.processor import EntityMerger
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_file(file: FileModel, config: ConfigManager, db: Session) -> bool:
    """Process a single file through PDF and Entity extraction stages"""
    try:
        # PDF Processing
        file.processing_status = "processing_pdf"
        db.commit()

        pdf_processor = PDFProcessor(file, config)
        pdf_result = pdf_processor.process()

        if not pdf_result.success:
            file.processing_status = "failed"
            file.processing_error = f"PDF processing failed: {pdf_result.message}"
            db.commit()
            return False

        file.markdown_path = pdf_result.markdown_path
        file.processing_status = "processing_entities"
        db.commit()

        # Entity Processing
        entity_processor = EntityProcessor(file, config)
        entity_result = entity_processor.process()

        if not entity_result.success:
            file.processing_status = "failed"
            file.processing_error = f"Entity extraction failed: {entity_result.message}"
            db.commit()
            return False

        file.entity_extraction_path = entity_result.analysis_path
        file.processing_status = "completed"
        file.last_processed_at = datetime.utcnow()
        db.commit()
        return True

    except Exception as e:
        logger.error(f"Error processing file {file.file_id}: {str(e)}")
        file.processing_status = "failed"
        file.processing_error = str(e)
        db.commit()
        return False


async def process_domain(
    domain_id: UUID, files: List[FileModel], config: ConfigManager, db: Session
):
    """Process domain-level analysis after all files are processed"""
    try:
        domain_processing = DomainProcessing(
            domain_id=domain_id, status="merging_entities", files=files
        )
        db.add(domain_processing)
        db.commit()

        # Merge entities from all files
        merger = EntityMerger(domain_processing, config)  # Pass config here
        merge_result = merger.process()

        if not merge_result.success:
            domain_processing.status = "failed"
            domain_processing.error = f"Entity merging failed: {merge_result.message}"
            db.commit()
            return

        domain_processing.merged_entities_path = merge_result.merged_path
        domain_processing.status = "processing_groups"
        db.commit()

        # Process groups
        group_processor = GroupProcessor(domain_processing, config)
        group_result = group_processor.process()

        if not group_result.success:
            domain_processing.status = "failed"
            domain_processing.error = f"Group analysis failed: {group_result.message}"
            db.commit()
            return

        domain_processing.entity_grouping_path = group_result.groups_path
        domain_processing.status = "processing_ontology"
        db.commit()

        # Generate ontology
        ontology_processor = OntologyProcessor(domain_processing, config)
        ontology_result = ontology_processor.process()

        if not ontology_result.success:
            domain_processing.status = "failed"
            domain_processing.error = (
                f"Ontology generation failed: {ontology_result.message}"
            )
        else:
            domain_processing.ontology_path = ontology_result.diagram_path
            domain_processing.status = "completed"
            domain_processing.completed_at = datetime.utcnow()

        db.commit()

    except Exception as e:
        logger.error(f"Error processing domain {domain_id}: {str(e)}")
        if domain_processing:
            domain_processing.status = "failed"
            domain_processing.error = str(e)
            db.commit()


async def process_all(domain_id: UUID, db: Session):
    """Main processing coordinator"""
    try:
        # Get domain info and setup config
        domain = db.query(Domain).filter(Domain.domain_id == domain_id).first()
        config = ConfigManager(db, str(domain.tenant_id), str(domain.domain_id))

        # Get all files for processing
        files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

        # Process all files first
        success = True
        for file in files:
            file_success = await process_file(file, config, db)
            success = success and file_success

        # If all files processed successfully, start domain processing
        if success:
            await process_domain(domain_id, files, config, db)

    finally:
        db.close()


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/process_files",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessingStatus,
    summary="Process all files in a domain",
)
async def start_processing(
    tenant_id: UUID,
    domain_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Validate domain exists
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get all files
    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()
    if not files:
        return ProcessingStatus(
            message="No files to process.", total_files=0, processing_started=False
        )

    # Queue processing
    for file in files:
        file.processing_status = "queued"
        file.processing_error = None
    db.commit()

    background_tasks.add_task(process_all, domain_id=domain_id, db=db)

    return ProcessingStatus(
        message=f"Processing started for {len(files)} files.",
        total_files=len(files),
        processing_started=True,
    )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/domain_processing_status",
    response_model=DomainProcessingSchema,
)
async def get_domain_processing_status(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    domain_processing = (
        db.query(DomainProcessing)
        .join(Domain)
        .filter(Domain.tenant_id == tenant_id, DomainProcessing.domain_id == domain_id)
        .order_by(DomainProcessing.created_at.desc())
        .first()
    )

    if not domain_processing:
        raise HTTPException(status_code=404, detail="No domain processing found")

    return domain_processing


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/processing_status",
    response_model=ProcessingStatus,
    summary="Get processing status for all files in a domain",
)
async def get_processing_status(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get the current processing status of all files in a domain.
    """
    # Validate domain exists and belongs to tenant
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get all files and their processing status
    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

    if not files:
        return ProcessingStatus(
            message="No files found.", total_files=0, processing_started=False
        )

    # Count files in each status
    total_files = len(files)
    completed = sum(1 for f in files if f.processing_status == "completed")
    failed = sum(1 for f in files if f.processing_status == "failed")
    processing = sum(
        1
        for f in files
        if f.processing_status in ["processing_pdf", "processing_entities", "queued"]
    )

    # Create detailed status message
    status_details = {
        "queued": sum(1 for f in files if f.processing_status == "queued"),
        "processing_pdf": sum(
            1 for f in files if f.processing_status == "processing_pdf"
        ),
        "processing_entities": sum(
            1 for f in files if f.processing_status == "processing_entities"
        ),
        "completed": completed,
        "failed": failed,
    }

    status_message = (
        f"Processing status: {completed} completed, {failed} failed, "
        f"{status_details['queued']} queued, "
        f"{status_details['processing_pdf']} processing PDF, "
        f"{status_details['processing_entities']} processing entities"
    )

    return ProcessingStatus(
        message=status_message,
        total_files=total_files,
        files_completed=completed,
        files_failed=failed,
        files_processing=processing,
        processing_started=True if processing > 0 else False,
        file_statuses=[
            FileStatus(
                file_id=str(f.file_id),
                filename=f.filename,
                status=f.processing_status,
                error=f.processing_error,
                markdown_path=f.markdown_path,
                entity_extraction_path=f.entity_extraction_path,
                last_processed_at=f.last_processed_at,
                processing_details=get_processing_details(f),
            )
            for f in files
        ],
    )


def get_processing_details(file: FileModel) -> Dict:
    """Get detailed processing information for a file."""
    details = {
        "current_stage": file.processing_status,
        "has_markdown": bool(file.markdown_path),
        "has_entity_extraction": bool(file.entity_extraction_path),
    }

    if file.processing_status == "completed":
        details["completed_stages"] = ["pdf_processing", "entity_extraction"]
    elif file.processing_status == "processing_entities":
        details["completed_stages"] = ["pdf_processing"]
    elif file.processing_status == "failed":
        details["completed_stages"] = ["pdf_processing"] if file.markdown_path else []
    else:
        details["completed_stages"] = []

    return details
