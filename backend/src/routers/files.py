from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os
import shutil
import logging

from ..models.models import Domain, File as FileModel, User
from ..models.schemas import FileResponse
from ..core.database import get_db
from ..core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration for file storage
BASE_FILE_PATH = "storage"  # Update this path as needed

# Ensure the base directory exists
os.makedirs(BASE_FILE_PATH, exist_ok=True)


def get_file_storage_path(domain_id: UUID, filename: str) -> str:
    domain_path = os.path.join(BASE_FILE_PATH, str(domain_id))
    os.makedirs(domain_path, exist_ok=True)
    return os.path.join(domain_path, filename)


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/upload",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to a specific domain",
)
def upload_file(
    tenant_id: UUID,
    domain_id: UUID,
    uploaded_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads a file and associates it with a specific domain.
    """
    # Validate the domain exists and belongs to the tenant
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Define the file storage path
    file_path = get_file_storage_path(domain_id, uploaded_file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file {uploaded_file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Create a new File record in the database
    new_file = FileModel(
        domain_id=domain_id,
        filename=uploaded_file.filename,
        filepath=file_path,
        uploaded_by=current_user.user_id,
    )
    db.add(new_file)
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Database commit failed for file {uploaded_file.filename}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to save file record to database"
        )
    db.refresh(new_file)

    return FileResponse(
        file_id=new_file.file_id,
        domain_id=new_file.domain_id,
        filename=new_file.filename,
        filepath=new_file.filepath,
        uploaded_at=new_file.uploaded_at,
        uploaded_by=new_file.uploaded_by,
    )


@router.delete(
    "/tenants/{tenant_id}/domains/{domain_id}/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific file from a domain",
)
def delete_file(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Deletes a file associated with a specific domain.
    """
    # Validate the file exists and is linked to the domain and tenant
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

    # Remove the file from the filesystem
    try:
        os.remove(file.filepath)
    except FileNotFoundError:
        logger.warning(f"File {file.filepath} not found on filesystem.")
    except Exception as e:
        logger.error(f"Error deleting file {file.filepath}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete file from filesystem"
        )

    # Remove the file record from the database
    db.delete(file)
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Database commit failed while deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete file record from database"
        )

    return


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/",
    response_model=List[FileResponse],
    summary="List all files in a specific domain",
)
def list_files(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieves a list of all files associated with a specific domain.
    """
    # Validate the domain exists and belongs to the tenant
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Retrieve all files linked to the domain
    files = db.query(FileModel).filter(FileModel.domain_id == domain_id).all()

    return [
        FileResponse(
            file_id=file.file_id,
            domain_id=file.domain_id,
            filename=file.filename,
            filepath=file.filepath,
            uploaded_at=file.uploaded_at,
            last_processed_at=file.last_processed_at,
            uploaded_by=file.uploaded_by,
        )
        for file in files
    ]
