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
    tenant_id: UUID, domain_data: DomainCreate, db: Session = Depends(get_db)
):
    """
    Creates a new domain and initializes its corresponding version tracking.
    """
    # Ensure the tenant exists
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Create the new domain
    new_domain = Domain(
        tenant_id=tenant_id,
        domain_name=domain_data.domain_name,
        description=domain_data.description,
        owner_user_id=domain_data.owner_user_id,
    )

    db.add(new_domain)
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating new domain: {e}")
        raise HTTPException(status_code=500, detail="Failed to create domain")
    db.refresh(new_domain)

    # Create the initial version for this domain
    new_domain_version = DomainVersion(
        domain_id=new_domain.domain_id,
        tenant_id=tenant_id,
        version=1,
    )

    db.add(new_domain_version)
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating domain version: {e}")
        raise HTTPException(status_code=500, detail="Failed to create domain version")
    db.refresh(new_domain_version)

    return new_domain


@router.get("/tenants/{tenant_id}/domains", response_model=List[DomainSchema])
def get_domains(tenant_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves all domains associated with a specific tenant.
    """
    # Ensure the tenant exists
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Query for all domains related to this tenant
    domains = db.query(Domain).filter(Domain.tenant_id == tenant_id).all()

    return domains


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainBasicResponse
)
async def get_domain_basic(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get basic domain information without processing results"""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get latest pipeline
    latest_pipeline = (
        db.query(ProcessingPipeline)
        .filter(ProcessingPipeline.domain_id == domain_id)
        .order_by(ProcessingPipeline.created_at.desc())
        .first()
    )

    # Get file count
    file_count = (
        db.query(func.count(File.file_id)).filter(File.domain_id == domain_id).scalar()
    )

    # Get version information
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

    # Convert pipeline to schema if it exists
    pipeline_data = None
    if latest_pipeline:
        file_ids = [file.file_id for file in latest_pipeline.files]
        pipeline_data = ProcessPipelineSchema(
            processing_id=latest_pipeline.pipeline_id,
            domain_id=latest_pipeline.domain_id,
            status=latest_pipeline.status,
            error=latest_pipeline.error,
            merged_entities_path=(
                getattr(latest_pipeline.current_merge, "output_path", None)
                if latest_pipeline.current_merge_id
                else None
            ),
            entity_grouping_path=(
                getattr(latest_pipeline.current_group, "output_path", None)
                if latest_pipeline.current_group_id
                else None
            ),
            ontology_path=(
                getattr(latest_pipeline.current_ontology, "output_path", None)
                if latest_pipeline.current_ontology_id
                else None
            ),
            created_at=latest_pipeline.created_at,
            completed_at=(
                latest_pipeline.completed_at
                if latest_pipeline.status == "completed"
                else None
            ),
            file_ids=file_ids,
        )

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


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/data", response_model=DomainDataSchema
)
async def get_domain_data(
    tenant_id: UUID,
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get domain data including processing results for a specific version"""
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get specific version or latest version
    domain_version = None
    if version:
        domain_version = (
            db.query(DomainVersion)
            .filter(
                DomainVersion.domain_id == domain_id, DomainVersion.version == version
            )
            .first()
        )
        if not domain_version:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
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
        # Get the associated pipeline and verify it completed successfully
        pipeline = domain_version.processing_pipeline
        if not pipeline or pipeline.status != "completed":
            raise HTTPException(
                status_code=404, detail="No completed processing found for this version"
            )

        # Load data from the version files
        with open(domain_version.entity_grouping_path, "r") as f:
            groups_data = json.load(f)

        with open(domain_version.ontology_path, "r") as f:
            ontology_data = json.load(f)

        # Get entities from the latest merge version
        latest_merge = pipeline.current_merge
        if not latest_merge or not latest_merge.output_path:
            raise HTTPException(status_code=404, detail="Merged entities not found")

        with open(latest_merge.output_path, "r") as f:
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
        logger.error(f"Error parsing processing results: {e}")
        raise HTTPException(status_code=500, detail="Error reading processing results")
    except Exception as e:
        logger.error(f"Error loading domain data: {e}")
        raise HTTPException(status_code=500, detail="Error loading domain data")


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/versions",
    response_model=DomainVersionSchema,
)
def create_domain_version(
    tenant_id: UUID, domain_id: UUID, processing_id: UUID, db: Session = Depends(get_db)
):
    """
    Creates a new domain version from a completed processing pipeline.
    """
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get the pipeline instead of domain processing
    pipeline = (
        db.query(ProcessingPipeline)
        .filter(
            ProcessingPipeline.pipeline_id == processing_id,
            ProcessingPipeline.status == "completed",
        )
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="No completed processing found")

    # Check for required versions
    if not pipeline.current_group or not pipeline.current_ontology:
        raise HTTPException(status_code=400, detail="Processing results incomplete")

    latest_version = (
        db.query(func.max(DomainVersion.version))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
        or 0
    )

    new_version = DomainVersion(
        domain_id=domain_id,
        tenant_id=tenant_id,
        version=latest_version + 1,
        processing_id=processing_id,
        entity_grouping_path=pipeline.current_group.output_path,
        ontology_path=pipeline.current_ontology.output_path,
    )

    db.add(new_version)
    try:
        db.commit()
        db.refresh(new_version)
        return new_version
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create version")


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
    """
    Retrieves all versions for a specific domain.
    """
    # Verify domain exists and belongs to tenant
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get all versions for this domain, ordered by version number
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
async def get_domain_version(
    tenant_id: UUID,
    domain_id: UUID,
    version: int,
    db: Session = Depends(get_db),
) -> DomainVersionSchema:
    """Get specific domain version with its file versions"""
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

    return DomainVersionSchema(
        domain_id=domain_version.domain_id,
        tenant_id=domain_version.tenant_id,
        version=domain_version.version,
        created_at=domain_version.created_at,
        status=domain_version.status,
        pipeline_id=domain_version.pipeline_id,
        file_versions=domain_version.file_versions,
    )
