from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Domain, User, DomainConfig
from ..models.schemas import (
    Domain as DomainSchema,
    Concept as ConceptSchema,
    Source as SourceSchema,
    Methodology as MethodologySchema,
    Relationship as RelationshipSchema,
    DomainConfig as DomainConfigSchema,
)

router = APIRouter()


# Get all domains related to the current authenticated user
@router.get("/", response_model=List[DomainSchema])
def get_domains(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    domains = (
        db.query(Domain).filter(Domain.owner_user_id == current_user.user_id).all()
    )

    if not domains:
        raise HTTPException(
            status_code=404, detail="No domains found for the current user"
        )
    return domains


# Get all concepts, sources, methodologies, and relationships related to a domain for the current user
@router.get("/{domain_id}/details", response_model=DomainSchema)
def get_domain_details(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .options(
            joinedload(Domain.concepts),  # Eager load concepts
            joinedload(Domain.sources),  # Eager load sources
            joinedload(Domain.methodologies),  # Eager load methodologies
            joinedload(Domain.relationships),  # Eager load relationships
        )
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    return domain


# Get all concepts related to a domain for the current user
@router.get("/{domain_id}/concepts", response_model=List[ConceptSchema])
def get_concepts_for_domain(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .options(joinedload(Domain.concepts))  # Eager load concepts
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    return domain.concepts


# Get all sources related to a domain for the current user
@router.get("/{domain_id}/sources", response_model=List[SourceSchema])
def get_sources_for_domain(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .options(joinedload(Domain.sources))  # Eager load sources
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    return domain.sources


# Get all methodologies related to a domain for the current user
@router.get("/{domain_id}/methodologies", response_model=List[MethodologySchema])
def get_methodologies_for_domain(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .options(joinedload(Domain.methodologies))  # Eager load methodologies
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    return domain.methodologies


# Get all relationships related to a domain for the current user
@router.get("/{domain_id}/relationships", response_model=List[RelationshipSchema])
def get_relationships_for_domain(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .options(joinedload(Domain.relationships))  # Eager load relationships
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    return domain.relationships


# New: Get domain configuration
@router.get("/{domain_id}/config", response_model=List[DomainConfigSchema])
def get_domain_config(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    config = db.query(DomainConfig).filter(DomainConfig.domain_id == domain_id).all()

    if not config:
        raise HTTPException(
            status_code=404, detail="No configuration found for this domain"
        )

    return config


# New: Update domain configuration
@router.put("/{domain_id}/config", response_model=DomainConfigSchema)
def update_domain_config(
    domain_id: UUID,
    config_key: str,
    config_value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .first()
    )

    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    domain_config = (
        db.query(DomainConfig)
        .filter(
            DomainConfig.domain_id == domain_id, DomainConfig.config_key == config_key
        )
        .first()
    )

    if not domain_config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    domain_config.config_value = config_value
    db.commit()
    db.refresh(domain_config)
    return domain_config
