from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID
import os
import shutil
import logging

from ..models.models import (
    Domain,
    File as FileModel,
    FileVersion,
    User,
    ProcessingPipeline,
)
from ..models.schemas import FileResponse, FileVersionResponse, FileWithVersionsResponse
from ..core.database import get_db
from ..core.security import get_current_user
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)
router = APIRouter()


def get_file_storage_path(
    config: ConfigManager, domain_id: UUID, filename: str, version: int
) -> str:
    """Generate versioned storage path for uploaded files"""
    processing_dir = config.get("processing_dir", "processing_output")
    domain_path = os.path.join(processing_dir, str(domain_id), "files")
    version_path = os.path.join(domain_path, str(version))
    os.makedirs(version_path, exist_ok=True)
    return os.path.join(version_path, filename)


def create_file_version(
    db: Session, file: FileModel, filepath: str, file_size: int
) -> FileVersion:
    """Create a new version for a file"""
    # Get latest version number
    latest_version = (
        db.query(func.max(FileVersion.version))
        .filter(FileVersion.file_id == file.file_id)
        .scalar()
        or 0
    )

    new_version = FileVersion(
        file_id=file.file_id,
        version=latest_version + 1,
        filepath=filepath,
        file_size=file_size,
    )

    db.add(new_version)
    return new_version


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/upload",
    response_model=FileWithVersionsResponse,
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

    # Check if file already exists
    existing_file = (
        db.query(FileModel)
        .filter(
            FileModel.domain_id == domain_id,
            FileModel.filename == uploaded_file.filename,
        )
        .first()
    )

    try:
        # Save uploaded file content
        file_contents = uploaded_file.file.read()
        file_size = len(file_contents)

        if existing_file:
            # Create new version for existing file
            file_path = get_file_storage_path(
                config,
                domain_id,
                uploaded_file.filename,
                len(existing_file.versions) + 1,
            )

            with open(file_path, "wb") as buffer:
                buffer.write(file_contents)

            new_version = create_file_version(db, existing_file, file_path, file_size)
            db.commit()

            return FileWithVersionsResponse(
                file_id=existing_file.file_id,
                domain_id=existing_file.domain_id,
                tenant_id=existing_file.tenant_id,
                filename=existing_file.filename,
                file_type=existing_file.file_type,
                file_size=file_size,
                original_path=existing_file.original_path,
                uploaded_at=existing_file.uploaded_at,
                uploaded_by=existing_file.uploaded_by,
                created_at=existing_file.created_at,
                versions=[
                    FileVersionResponse.from_orm(v)
                    for v in sorted(existing_file.versions, key=lambda x: x.version)
                ],
            )
        else:
            # Create new file record
            file_path = get_file_storage_path(
                config, domain_id, uploaded_file.filename, 1
            )

            with open(file_path, "wb") as buffer:
                buffer.write(file_contents)

            new_file = FileModel(
                domain_id=domain_id,
                tenant_id=tenant_id,
                filename=uploaded_file.filename,
                file_type=uploaded_file.filename.split(".")[-1].lower(),
                file_size=file_size,
                original_path=file_path,
                uploaded_by=current_user.user_id,
            )

            db.add(new_file)
            db.flush()  # Get new_file.file_id

            # Create initial version
            new_version = create_file_version(db, new_file, file_path, file_size)
            db.commit()

            return FileWithVersionsResponse(
                file_id=new_file.file_id,
                domain_id=new_file.domain_id,
                tenant_id=new_file.tenant_id,
                filename=new_file.filename,
                file_type=new_file.file_type,
                file_size=new_file.file_size,
                original_path=new_file.original_path,
                uploaded_at=new_file.uploaded_at,
                uploaded_by=new_file.uploaded_by,
                created_at=new_file.created_at,
                versions=[FileVersionResponse.from_orm(new_version)],
            )

    except Exception as e:
        logger.error(f"Failed to save file {uploaded_file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/files/{file_id}/versions",
    response_model=FileVersionResponse,
)
async def create_file_version_endpoint(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    uploaded_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new version for an existing file"""
    file = (
        db.query(FileModel)
        .filter(FileModel.file_id == file_id, FileModel.domain_id == domain_id)
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    config = ConfigManager(db, str(tenant_id), str(domain_id))

    try:
        file_contents = uploaded_file.file.read()
        file_size = len(file_contents)

        file_path = get_file_storage_path(
            config, domain_id, file.filename, len(file.versions) + 1
        )

        with open(file_path, "wb") as buffer:
            buffer.write(file_contents)

        new_version = create_file_version(db, file, file_path, file_size)
        db.commit()

        return FileVersionResponse.from_orm(new_version)

    except Exception as e:
        logger.error(f"Failed to create new version: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create version: {str(e)}"
        )


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/files/{file_id}/versions/{version}",
    response_model=FileVersionResponse,
)
async def get_file_version(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    version: int,
    db: Session = Depends(get_db),
):
    """Get specific version of a file"""
    file_version = (
        db.query(FileVersion)
        .join(FileModel)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            FileModel.domain_id == domain_id,
            FileVersion.file_id == file_id,
            FileVersion.version == version,
        )
        .first()
    )

    if not file_version:
        raise HTTPException(status_code=404, detail="File version not found")

    return FileVersionResponse.from_orm(file_version)


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/files/{file_id}/versions",
    response_model=List[FileVersionResponse],
)
async def list_file_versions(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
):
    """List all versions of a file"""
    file = (
        db.query(FileModel)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            FileModel.domain_id == domain_id,
            FileModel.file_id == file_id,
        )
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    versions = sorted(file.versions, key=lambda x: x.version)
    return [FileVersionResponse.from_orm(v) for v in versions]


# Keep existing endpoints but update their implementations
@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/files",
    response_model=List[FileWithVersionsResponse],
)
def list_files(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """List all files in a domain with their versions"""
    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

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
                FileVersionResponse.from_orm(v)
                for v in sorted(file.versions, key=lambda x: x.version)
            ],
        )
        for file in files
    ]


@router.delete("/tenants/{tenant_id}/domains/{domain_id}/files/{file_id}")
async def delete_file(
    tenant_id: UUID,
    domain_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a file and all its versions"""
    file = (
        db.query(FileModel)
        .join(Domain)
        .filter(
            Domain.tenant_id == tenant_id,
            FileModel.domain_id == domain_id,
            FileModel.file_id == file_id,
        )
        .first()
    )

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete all version files
    for version in file.versions:
        if os.path.exists(version.filepath):
            try:
                os.remove(version.filepath)
            except Exception as e:
                logger.warning(f"Failed to remove version file {version.filepath}: {e}")

    # Delete database record (will cascade to versions)
    db.delete(file)
    db.commit()

    return {"message": "File and all versions deleted successfully"}
