from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
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
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainUpdate,
    DomainDataSchema,
    DomainVersionSchema,
    ProcessPipelineSchema,
    DomainBasicResponse,
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
            version=1,
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
        db.query(func.max(DomainVersion.version))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
    )
    version_count = (
        db.query(func.count(DomainVersion.version))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
    )

    pipeline_data = None
    if latest_pipeline:
        pipeline_data = ProcessPipelineSchema.from_orm(latest_pipeline)

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
                DomainVersion.domain_id == domain_id, DomainVersion.version == version
            )
            .first()
        )
    else:
        domain_version = (
            db.query(DomainVersion)
            .filter(DomainVersion.domain_id == domain_id)
            .order_by(DomainVersion.version.desc())
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
    """Retrieves all versions for a specific domain."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    versions = (
        db.query(DomainVersion)
        .filter(DomainVersion.domain_id == domain_id)
        .order_by(DomainVersion.version.asc())
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
            DomainVersion.version == version,
        )
        .first()
    )
    if not domain_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    return DomainVersionSchema.from_orm(domain_version)


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
    """Creates a new version for a domain."""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    latest_version = (
        db.query(func.max(DomainVersion.version))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
        or 0
    )

    new_version = DomainVersion(
        domain_id=domain_id, tenant_id=tenant_id, version=latest_version + 1
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
