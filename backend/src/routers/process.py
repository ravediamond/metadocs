from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Dict
import logging

from ..models.models import Domain, File as FileModel
from ..models.schemas import ProcessingStatus, FileStatus
from ..core.database import get_db
from ..processors.pdf.processor import PDFProcessor
from ..processors.entity.processor import EntityProcessor

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_file_background(file_id: UUID, db: Session):
    """Background task to process a single file"""
    try:
        # Get a new database session for this background task
        file = db.query(FileModel).filter(FileModel.file_id == file_id).first()
        if not file:
            logger.error(f"File {file_id} not found")
            return

        # Step 1: PDF Processing
        logger.info(f"Starting PDF processing for file {file_id}")
        file.processing_status = "processing_pdf"
        db.commit()

        pdf_processor = PDFProcessor(file)
        pdf_result = pdf_processor.process()

        if not pdf_result.success:
            logger.error(
                f"PDF processing failed for file {file_id}: {pdf_result.message}"
            )
            file.processing_status = "failed"
            file.processing_error = f"PDF processing failed: {pdf_result.message}"
            db.commit()
            return

        file.markdown_path = pdf_result.markdown_path
        logger.info(f"PDF processing completed for file {file_id}")

        # Step 2: Entity Extraction
        logger.info(f"Starting entity extraction for file {file_id}")
        file.processing_status = "processing_entities"
        db.commit()

        entity_processor = EntityProcessor(file)
        entity_result = entity_processor.process()

        if entity_result.success:
            file.entity_extraction_path = entity_result.analysis_path
            file.processing_status = "completed"
            file.last_processed_at = datetime.utcnow()
            logger.info(f"Entity extraction completed for file {file_id}")
        else:
            logger.error(
                f"Entity extraction failed for file {file_id}: {entity_result.message}"
            )
            file.processing_status = "failed"
            file.processing_error = f"Entity extraction failed: {entity_result.message}"

        db.commit()

    except Exception as e:
        logger.error(f"Error processing file {file_id}: {str(e)}")
        if file:
            file.processing_status = "failed"
            file.processing_error = str(e)
            db.commit()

    finally:
        db.close()


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/process_files",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessingStatus,
    summary="Process all files in a domain",
)
async def process_files(
    tenant_id: UUID,
    domain_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Initiates processing of all files associated with a specific domain.
    Processing includes PDF conversion and entity extraction.
    """
    # Validate domain exists and belongs to tenant
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get all files for the domain
    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

    if not files:
        return ProcessingStatus(
            message="No files to process.", total_files=0, processing_started=False
        )

    # Initialize processing for each file
    for file in files:
        file.processing_status = "queued"
        file.processing_error = None
        background_tasks.add_task(process_file_background, file_id=file.file_id, db=db)

    db.commit()

    return ProcessingStatus(
        message=f"Processing started for {len(files)} files.",
        total_files=len(files),
        processing_started=True,
    )


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
