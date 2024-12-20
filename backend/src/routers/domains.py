from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from typing import List
from uuid import UUID
import logging
import json

from ..models.models import (
    Domain,
    DomainVersion,
    Tenant,
    DomainProcessing,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainDataSchema,
    DomainVersionSchema,
)
from ..core.database import get_db

from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tenants/{tenant_id}/domains", response_model=DomainSchema)
def create_domain(
    tenant_id: UUID, domain_data: DomainCreate, db: Session = Depends(get_db)
):
    """
    Creates a new domain and initializes its corresponding Apache AGE graph.
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


@router.get("/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainDataSchema)
def get_domain_details(tenant_id: UUID, domain_id: UUID, db: Session = Depends(get_db)):
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get latest domain processing
    domain_processing = (
        db.query(DomainProcessing)
        .filter(
            DomainProcessing.domain_id == domain_id,
            DomainProcessing.status == "completed",
        )
        .order_by(DomainProcessing.created_at.desc())
        .first()
    )

    if not domain_processing:
        raise HTTPException(status_code=404, detail="No completed processing found")

    try:
        with open(domain_processing.merged_entities_path, "r") as f:
            entities_data = json.load(f)
        with open(domain_processing.entity_grouping_path, "r") as f:
            groups_data = json.load(f)
        with open(domain_processing.ontology_path, "r") as f:
            ontology = json.load(f)

        return DomainDataSchema(
            domain_id=domain.domain_id,
            domain_name=domain.domain_name,
            description=domain.description,
            tenant_id=tenant_id,
            created_at=domain.created_at,
            processing_id=domain_processing.processing_id,
            entities=entities_data,
            groups=groups_data["groups"],
            ontology=ontology,
            last_processed_at=domain_processing.completed_at,
        )

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
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    domain_processing = (
        db.query(DomainProcessing)
        .filter(
            DomainProcessing.processing_id == processing_id,
            DomainProcessing.status == "completed",
        )
        .first()
    )

    if not domain_processing:
        raise HTTPException(status_code=404, detail="No completed processing found")

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
        entity_grouping_path=domain_processing.entity_grouping_path,
        ontology_path=domain_processing.ontology_path,
    )

    db.add(new_version)
    try:
        db.commit()
        db.refresh(new_version)
        return new_version
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create version")
