from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
import logging
import json

from ..models.models import (
    Domain,
    DomainVersion,
    Tenant,
    ProcessingPipeline,
    User,
    File,
    DomainVersionFile,
    FileVersion,
    PipelineStatus,
    PipelineStage,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainUpdate,
    DomainDataSchema,
    DomainVersionSchema,
    ProcessingPipeline as ProcessingPipelineSchema,
    DomainBasicResponse,
    DomainVersionFile as DomainVersionFileSchema,
    FileVersionsRequest,
)
from ..core.database import get_db
from ..core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tenants/{tenant_id}/domains", response_model=DomainSchema)
def create_domain(
    tenant_id: UUID,
    domain_data: DomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new domain and initializes its corresponding version tracking."""
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    new_domain = Domain(
        tenant_id=tenant_id,
        domain_name=domain_data.domain_name,
        description=domain_data.description,
        owner_user_id=current_user.user_id,
    )

    db.add(new_domain)
    try:
        db.commit()
        db.refresh(new_domain)

        # Create initial version
        new_version = DomainVersion(
            domain_id=new_domain.domain_id,
            tenant_id=tenant_id,
            version_number=1,
        )
        db.add(new_version)
        db.commit()

        return new_domain
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating domain: {e}")
        raise HTTPException(status_code=500, detail="Failed to create domain")


@router.get("/tenants/{tenant_id}/domains", response_model=List[DomainSchema])
def get_domains(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all domains associated with a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    domains = db.query(Domain).filter(Domain.tenant_id == tenant_id).all()
    return domains


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainBasicResponse
)
def get_domain(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get basic domain information."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    latest_pipeline = (
        db.query(ProcessingPipeline)
        .filter(ProcessingPipeline.domain_id == domain_id)
        .order_by(ProcessingPipeline.created_at.desc())
        .first()
    )

    file_count = (
        db.query(func.count(File.file_id)).filter(File.domain_id == domain_id).scalar()
    )

    latest_version = (
        db.query(func.max(DomainVersion.version_number))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
    )
    version_count = (
        db.query(func.count(DomainVersion.version_number))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
    )

    pipeline_data = None
    if latest_pipeline:
        pipeline_data = ProcessingPipelineSchema.from_orm(latest_pipeline)

    return DomainBasicResponse(
        domain_id=domain.domain_id,
        domain_name=domain.domain_name,
        description=domain.description,
        tenant_id=domain.tenant_id,
        created_at=domain.created_at,
        owner_user_id=domain.owner_user_id,
        latest_pipeline=pipeline_data,
        file_count=file_count,
        version_count=version_count,
        latest_version=latest_version,
    )


@router.patch("/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainSchema)
def update_domain(
    tenant_id: UUID,
    domain_id: UUID,
    domain_update: DomainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update domain information."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    for field, value in domain_update.dict(exclude_unset=True).items():
        setattr(domain, field, value)

    try:
        db.commit()
        db.refresh(domain)
        return domain
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error updating domain: {e}")
        raise HTTPException(status_code=500, detail="Failed to update domain")


@router.delete("/tenants/{tenant_id}/domains/{domain_id}")
def delete_domain(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a domain and all associated data."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    try:
        db.delete(domain)
        db.commit()
        return {"message": "Domain deleted successfully"}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error deleting domain: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete domain")


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/data", response_model=DomainDataSchema
)
def get_domain_data(
    tenant_id: UUID,
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get domain data including processing results for a specific version."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    domain_version = None
    if version:
        domain_version = (
            db.query(DomainVersion)
            .filter(
                DomainVersion.domain_id == domain_id,
                DomainVersion.version_number == version,
            )
            .first()
        )
    else:
        domain_version = (
            db.query(DomainVersion)
            .filter(DomainVersion.domain_id == domain_id)
            .order_by(DomainVersion.version_number.desc())
            .first()
        )

    if not domain_version:
        raise HTTPException(status_code=404, detail="No processed versions found")

    try:
        pipeline = domain_version.processing_pipeline
        if not pipeline or pipeline.status != "completed":
            raise HTTPException(status_code=404, detail="No completed processing found")

        # Load all required data files
        with open(pipeline.current_group.output_path, "r") as f:
            groups_data = json.load(f)

        with open(pipeline.current_ontology.output_path, "r") as f:
            ontology_data = json.load(f)

        with open(pipeline.current_merge.output_path, "r") as f:
            entities_data = json.load(f)

        return DomainDataSchema(
            domain_id=domain.domain_id,
            domain_name=domain.domain_name,
            description=domain.description,
            tenant_id=domain.tenant_id,
            created_at=domain.created_at,
            entities=entities_data,
            groups=groups_data["groups"],
            ontology=ontology_data,
            processing_id=pipeline.pipeline_id,
            last_processed_at=domain_version.created_at,
        )
    except FileNotFoundError as e:
        logger.error(f"Missing processing file: {e}")
        raise HTTPException(
            status_code=404, detail="Processing results files not found"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing results: {e}")
        raise HTTPException(status_code=500, detail="Error reading processing results")
    except Exception as e:
        logger.error(f"Error loading domain data: {e}")
        raise HTTPException(status_code=500, detail="Error loading domain data")


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/versions",
    response_model=List[DomainVersionSchema],
)
def get_domain_versions(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all versions for a specific domain with their pipelines."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    versions = (
        db.query(DomainVersion)
        .options(joinedload(DomainVersion.processing_pipeline))  # Eager load pipeline
        .filter(DomainVersion.domain_id == domain_id)
        .order_by(DomainVersion.version_number.asc())
        .all()
    )
    return versions


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{version}",
    response_model=DomainVersionSchema,
)
def get_domain_version(
    tenant_id: UUID,
    domain_id: UUID,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get specific domain version details."""
    domain_version = (
        db.query(DomainVersion)
        .filter(
            DomainVersion.domain_id == domain_id,
            DomainVersion.tenant_id == tenant_id,
            DomainVersion.version_number == version,
        )
        .first()
    )
    if not domain_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    return domain_version


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions",
    response_model=DomainVersionSchema,
)
def create_domain_version(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new version for a domain with an associated pipeline."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    latest_version = (
        db.query(func.max(DomainVersion.version_number))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
        or 0
    )

    # Create new pipeline
    pipeline = ProcessingPipeline(
        domain_id=domain_id,
        stage=PipelineStage.NOT_STARTED,
        status=PipelineStatus.UNINITIALIZED,
    )
    db.add(pipeline)
    db.flush()  # Flush to get pipeline_id

    new_version = DomainVersion(
        domain_id=domain_id,
        tenant_id=tenant_id,
        version_number=latest_version + 1,
        pipeline_id=pipeline.pipeline_id,  # Associate the pipeline
    )

    try:
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        return new_version
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating version: {e}")
        raise HTTPException(status_code=500, detail="Failed to create version")


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{version}/files",
    response_model=List[DomainVersionFileSchema],
)
async def add_files_to_version(
    tenant_id: UUID,
    domain_id: UUID,
    version: int,
    file_versions: FileVersionsRequest,
    db: Session = Depends(get_db),
):
    domain_version = (
        db.query(DomainVersion)
        .filter(
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == version,
            DomainVersion.tenant_id == tenant_id,
        )
        .first()
    )

    if not domain_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    new_version_files = []
    for file_version_id in file_versions.file_version_ids:
        version_file = DomainVersionFile(
            domain_id=domain_id,
            version_number=version,
            file_version_id=file_version_id,
        )
        db.add(version_file)
        new_version_files.append(version_file)

    try:
        db.commit()
        return new_version_files
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{version}/files/{file_version_id}",
)
async def remove_file_from_version(
    tenant_id: UUID,
    domain_id: UUID,
    version: int,
    file_version_id: UUID,
    db: Session = Depends(get_db),
):
    version_file = (
        db.query(DomainVersionFile)
        .filter(
            DomainVersionFile.domain_id == domain_id,
            DomainVersionFile.version_number == version,
            DomainVersionFile.file_version_id == file_version_id,
        )
        .first()
    )

    if not version_file:
        raise HTTPException(status_code=404, detail="File not found in version")

    try:
        db.delete(version_file)
        db.commit()
        return {"message": "File removed from version"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{version}/files/{file_version_id}",
    response_model=DomainVersionFileSchema,
)
def get_domain_version_file(
    tenant_id: UUID,
    domain_id: UUID,
    version: int,
    file_version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific file in a domain version."""
    version_file = (
        db.query(DomainVersionFile, FileVersion.filename)
        .join(
            FileVersion,
            DomainVersionFile.file_version_id == FileVersion.file_version_id,
        )
        .filter(
            DomainVersionFile.domain_id == domain_id,
            DomainVersionFile.version_number == version,
            DomainVersionFile.file_version_id == file_version_id,
        )
        .first()
    )

    if not version_file:
        raise HTTPException(status_code=404, detail="File not found in version")

    # Create a dictionary with all fields from DomainVersionFile
    result = {
        "domain_id": version_file[0].domain_id,
        "version_number": version_file[0].version_number,
        "file_version_id": version_file[0].file_version_id,
        "error": version_file[0].error,
        "created_at": version_file[0].created_at,
        "filename": version_file[1],
    }

    return result


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/versions/{version}/files",
    response_model=List[DomainVersionFileSchema],
)
def list_domain_version_files(
    tenant_id: UUID,
    domain_id: UUID,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all files associated with a domain version."""
    domain_version = (
        db.query(DomainVersion)
        .filter(
            DomainVersion.domain_id == domain_id,
            DomainVersion.version_number == version,
            DomainVersion.tenant_id == tenant_id,
        )
        .first()
    )

    if not domain_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    version_files = (
        db.query(DomainVersionFile, FileVersion.filename)
        .join(
            FileVersion,
            DomainVersionFile.file_version_id == FileVersion.file_version_id,
        )
        .filter(
            DomainVersionFile.domain_id == domain_id,
            DomainVersionFile.version_number == version,
        )
        .all()
    )

    results = []
    for vf in version_files:
        result = {
            "domain_id": vf[0].domain_id,
            "version_number": vf[0].version_number,
            "file_version_id": vf[0].file_version_id,
            "error": vf[0].error,
            "created_at": vf[0].created_at,
            "filename": vf[1],
        }
        results.append(result)

    return results
