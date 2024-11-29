from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os
import shutil
import logging

from ..models.models import (
    Domain,
    File as FileModel,
    User,
    ProcessingPipeline,
)
from ..models.schemas import FileResponse, FileVersionResponse, FileWithVersionsResponse
from ..core.database import get_db
from ..core.security import get_current_user
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


def get_file_response(file: FileModel) -> FileResponse:
    """Convert File model to FileResponse schema"""
    # Get latest file version
    latest_version = (
        max(file.versions, key=lambda v: v.version) if file.versions else None
    )

    return FileResponse(
        file_id=file.file_id,
        domain_id=file.domain_id,
        tenant_id=file.tenant_id,
        filename=file.filename,
        file_type=file.file_type,
        file_size=file.file_size,
        original_path=file.original_path,
        uploaded_at=file.uploaded_at,
        uploaded_by=file.uploaded_by,
        created_at=file.created_at,
        versions=(
            [version.version for version in file.versions] if file.versions else []
        ),
    )


def get_file_storage_path(config: ConfigManager, domain_id: UUID, filename: str) -> str:
    """Generate storage path for uploaded files"""
    processing_dir = config.get("processing_dir", "processing_output")
    domain_path = os.path.join(processing_dir, str(domain_id))
    os.makedirs(domain_path, exist_ok=True)
    return os.path.join(domain_path, filename)


def cleanup_pipeline_files(pipeline: ProcessingPipeline):
    """Clean up files associated with a processing pipeline"""
    if not pipeline:
        return

    # Get all version objects that might have output files
    versions = [
        pipeline.current_parse,
        pipeline.current_extract,
        pipeline.current_merge,
        pipeline.current_group,
        pipeline.current_ontology,
        pipeline.current_graph,
    ]

    # Clean up output files from all versions
    for version in versions:
        if version and version.output_path and os.path.exists(version.output_path):
            try:
                os.remove(version.output_path)
            except Exception as e:
                logger.warning(f"Failed to remove version output file: {e}")


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/upload",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_file(
    tenant_id: UUID,
    domain_id: UUID,
    uploaded_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a new file to a domain"""
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    config = ConfigManager(db, str(tenant_id), str(domain_id))
    processing_dir = config.get("processing_dir", "processing_output")
    os.makedirs(processing_dir, exist_ok=True)

    file_path = get_file_storage_path(config, domain_id, uploaded_file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file {uploaded_file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    new_file = FileModel(
        domain_id=domain_id,
        filename=uploaded_file.filename,
        filepath=file_path,
        uploaded_by=current_user.user_id,
        processing_status="queued",
    )

    db.add(new_file)
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Database commit failed for file {uploaded_file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file record")
    db.refresh(new_file)

    return get_file_response(new_file)


@router.delete(
    "/tenants/{tenant_id}/domains/{domain_id}/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_file(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a file and its associated processing data"""
    file = (
        db.query(FileModel)
        .join(Domain)
        .filter(
            FileModel.file_id == file_id,
            FileModel.domain_id == domain_id,
            Domain.tenant_id == tenant_id,
        )
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # List of paths to cleanup
    paths_to_remove = [
        file.filepath,
        file.markdown_path,
        file.entity_extraction_path,
    ]

    for path in paths_to_remove:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove file {path}: {e}")

    # Get all pipelines that might be affected by this file's deletion
    pipelines = (
        db.query(ProcessingPipeline)
        .filter(ProcessingPipeline.domain_id == domain_id)
        .all()
    )

    # Clean up pipeline files if needed
    for pipeline in pipelines:
        cleanup_pipeline_files(pipeline)

    db.delete(file)
    db.commit()
    return


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/",
    response_model=List[FileResponse],
)
def list_files(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """List all files in a domain"""
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()
    return [get_file_response(file) for file in files]


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/files",
    response_model=List[FileWithVersionsResponse],
)
def get_domain_files_with_versions(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all files and their versions for a domain"""
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Query files with their versions using joined loading
    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

    return [
        FileWithVersionsResponse(
            file_id=file.file_id,
            domain_id=file.domain_id,
            tenant_id=file.tenant_id,
            filename=file.filename,
            file_type=file.file_type,
            file_size=file.file_size,
            original_path=file.original_path,
            uploaded_at=file.uploaded_at,
            uploaded_by=file.uploaded_by,
            created_at=file.created_at,
            versions=[
                FileVersionResponse(
                    file_version_id=version.file_version_id,
                    file_id=version.file_id,
                    version=version.version,
                    filepath=version.filepath,
                    created_at=version.created_at,
                )
                for version in file.versions
            ],
        )
        for file in files
    ]
