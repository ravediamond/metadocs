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
    DomainProcessing,
    DomainProcessingFiles,
)
from ..models.schemas import FileResponse
from ..core.database import get_db
from ..core.security import get_current_user
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

os.makedirs(settings.PROCESSING_DIR, exist_ok=True)


def get_file_response(file: FileModel) -> FileResponse:
    return FileResponse(
        file_id=file.file_id,
        domain_id=file.domain_id,
        filename=file.filename,
        filepath=file.filepath,
        uploaded_at=file.uploaded_at,
        uploaded_by=file.uploaded_by,
        last_processed_at=file.last_processed_at,
        processing_status=file.processing_status,
        processing_error=file.processing_error,
        markdown_path=file.markdown_path,
        entity_extraction_path=file.entity_extraction_path,
        entity_grouping_path=file.entity_grouping_path,
        ontology_path=file.ontology_path,
    )


def get_file_storage_path(domain_id: UUID, filename: str) -> str:
    domain_path = os.path.join(settings.PROCESSING_DIR, str(domain_id))
    os.makedirs(domain_path, exist_ok=True)
    return os.path.join(domain_path, filename)


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
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    file_path = get_file_storage_path(domain_id, uploaded_file.filename)

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

    return FileResponse(
        file_id=new_file.file_id,
        domain_id=new_file.domain_id,
        filename=new_file.filename,
        filepath=new_file.filepath,
        uploaded_at=new_file.uploaded_at,
        uploaded_by=new_file.uploaded_by,
        last_processed_at=new_file.last_processed_at,
        processing_status=new_file.processing_status,
        processing_error=new_file.processing_error,
        markdown_path=new_file.markdown_path,
        entity_extraction_path=new_file.entity_extraction_path,
    )


@router.delete(
    "/tenants/{tenant_id}/domains/{domain_id}/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_file(
    tenant_id: UUID, domain_id: UUID, file_id: UUID, db: Session = Depends(get_db)
):
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
        file.entity_grouping_path,
        file.ontology_path,
    ]

    for path in paths_to_remove:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove file {path}: {e}")

    # Also check domain processing that uses this file
    domain_processings = (
        db.query(DomainProcessing)
        .join(DomainProcessingFiles)
        .filter(DomainProcessingFiles.file_id == file_id)
        .all()
    )

    for processing in domain_processings:
        if processing.merged_entities_path and os.path.exists(
            processing.merged_entities_path
        ):
            try:
                os.remove(processing.merged_entities_path)
            except Exception as e:
                logger.warning(f"Failed to remove merged entities file: {e}")

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
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

    return [
        FileResponse(
            file_id=file.file_id,
            domain_id=file.domain_id,
            filename=file.filename,
            filepath=file.filepath,
            uploaded_at=file.uploaded_at,
            uploaded_by=file.uploaded_by,
            last_processed_at=file.last_processed_at,
            processing_status=file.processing_status,
            processing_error=file.processing_error,
            markdown_path=file.markdown_path,
            entity_extraction_path=file.entity_extraction_path,
        )
        for file in files
    ]
