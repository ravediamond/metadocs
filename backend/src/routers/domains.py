from uuid import UUID
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import (
    Domain,
    User,
    Concept,
    Source,
    Methodology,
    Relationship,
    DomainConfig,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainDataSchema,
    Concept as ConceptSchema,
    Source as SourceSchema,
    Methodology as MethodologySchema,
    Relationship as RelationshipSchema,
    ConceptCreate as ConceptCreateSchema,
    SourceCreate as SourceCreateSchema,
    MethodologyCreate as MethodologyCreateSchema,
    RelationshipCreate as RelationshipCreateSchema,
    DomainConfig as DomainConfigSchema,
    DomainDataSchema,
    DomainSaveSchema,
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
@router.get("/{domain_id}/details", response_model=DomainDataSchema)
def get_domain_details(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Query for the domain and check if the user has access to it
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

    # If no version is specified, use the current domain version
    if version is None:
        version = domain.version

    # Query the concepts, sources, methodologies, and relationships based on the domain version
    concepts = (
        db.query(Concept)
        .filter(
            Concept.domain_id == domain_id,
            Concept.domain_version == version,
        )
        .all()
    )

    sources = (
        db.query(Source)
        .filter(
            Source.domain_id == domain_id,
            Source.domain_version == version,
        )
        .all()
    )

    methodologies = (
        db.query(Methodology)
        .filter(
            Methodology.domain_id == domain_id,
            Methodology.domain_version == version,
        )
        .all()
    )

    relationships = (
        db.query(Relationship)
        .filter(
            Relationship.domain_id == domain_id,
            Relationship.domain_version == version,
        )
        .all()
    )

    # Return the domain's metadata and related entities
    return DomainDataSchema(
        domain_id=domain.domain_id,
        domain_name=domain.domain_name,
        description=domain.description,
        version=version,
        created_at=domain.created_at,
        concepts=concepts,
        sources=sources,
        methodologies=methodologies,
        relationships=relationships,
    )


# Save the domain with new version
@router.post("/{domain_id}/save", response_model=DomainSchema)
def save_domain(
    domain_id: UUID,
    domain_data: DomainSaveSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if domain exists and belongs to the user
    latest_domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id, Domain.owner_user_id == current_user.user_id
        )
        .order_by(Domain.version.desc())
        .first()
    )
    if not latest_domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    # Create a new domain version
    new_version = latest_domain.version + 1
    new_domain = Domain(
        domain_id=domain_id,
        version=new_version,
        domain_name=latest_domain.domain_name,
        owner_user_id=current_user.user_id,
        description=latest_domain.description,
        created_at=func.now(),
    )
    db.add(new_domain)
    db.commit()

    # Copy existing entities to the new version
    # Concepts
    existing_concepts = (
        db.query(Concept)
        .filter(
            Concept.domain_id == domain_id,
            Concept.domain_version == latest_domain.version,
        )
        .all()
    )
    for concept in existing_concepts:
        new_concept = Concept(
            concept_id=concept.concept_id,
            domain_id=concept.domain_id,
            domain_version=new_version,
            name=concept.name,
            description=concept.description,
            type=concept.type,
            embedding=concept.embedding,
            created_at=concept.created_at,
            updated_at=concept.updated_at,
        )
        db.add(new_concept)

    # Sources
    existing_sources = (
        db.query(Source)
        .filter(
            Source.domain_id == domain_id,
            Source.domain_version == latest_domain.version,
        )
        .all()
    )
    for source in existing_sources:
        new_source = Source(
            source_id=source.source_id,
            domain_id=source.domain_id,
            domain_version=new_version,
            name=source.name,
            description=source.description,
            source_type=source.source_type,
            location=source.location,
            created_at=source.created_at,
        )
        db.add(new_source)

    # Methodologies
    existing_methodologies = (
        db.query(Methodology)
        .filter(
            Methodology.domain_id == domain_id,
            Methodology.domain_version == latest_domain.version,
        )
        .all()
    )
    for methodology in existing_methodologies:
        new_methodology = Methodology(
            methodology_id=methodology.methodology_id,
            domain_id=methodology.domain_id,
            domain_version=new_version,
            name=methodology.name,
            description=methodology.description,
            steps=methodology.steps,
            created_at=methodology.created_at,
        )
        db.add(new_methodology)

    # Relationships
    existing_relationships = (
        db.query(Relationship)
        .filter(
            Relationship.domain_id == domain_id,
            Relationship.domain_version == latest_domain.version,
        )
        .all()
    )
    for relationship in existing_relationships:
        new_relationship = Relationship(
            relationship_id=relationship.relationship_id,
            domain_id=relationship.domain_id,
            domain_version=new_version,
            entity_id_1=relationship.entity_id_1,
            entity_type_1=relationship.entity_type_1,
            entity_id_2=relationship.entity_id_2,
            entity_type_2=relationship.entity_type_2,
            relationship_type=relationship.relationship_type,
            created_at=relationship.created_at,
        )
        db.add(new_relationship)

    db.commit()

    # Apply updates from domain_data
    # Concepts
    for concept_data in domain_data.concepts:
        concept = (
            db.query(Concept)
            .filter(
                Concept.concept_id == concept_data.concept_id,
                Concept.domain_id == domain_id,
                Concept.domain_version == new_version,
            )
            .first()
        )

        if concept:
            # Update existing concept
            concept.name = concept_data.name
            concept.description = concept_data.description
            concept.type = concept_data.type
            concept.updated_at = func.now()
        else:
            # Add new concept
            new_concept = Concept(
                concept_id=concept_data.concept_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version,
                name=concept_data.name,
                description=concept_data.description,
                type=concept_data.type,
            )
            db.add(new_concept)

    # Sources
    for source_data in domain_data.sources:
        source = (
            db.query(Source)
            .filter(
                Source.source_id == source_data.source_id,
                Source.domain_id == domain_id,
                Source.domain_version == new_version,
            )
            .first()
        )

        if source:
            # Update existing source
            source.name = source_data.name
            source.description = source_data.description
            source.source_type = source_data.source_type
            source.location = source_data.location
        else:
            # Add new source
            new_source = Source(
                source_id=source_data.source_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version,
                name=source_data.name,
                description=source_data.description,
                source_type=source_data.source_type,
                location=source_data.location,
            )
            db.add(new_source)

    # Methodologies
    for methodology_data in domain_data.methodologies:
        methodology = (
            db.query(Methodology)
            .filter(
                Methodology.methodology_id == methodology_data.methodology_id,
                Methodology.domain_id == domain_id,
                Methodology.domain_version == new_version,
            )
            .first()
        )

        if methodology:
            # Update existing methodology
            methodology.name = methodology_data.name
            methodology.description = methodology_data.description
            methodology.steps = methodology_data.steps
        else:
            # Add new methodology
            new_methodology = Methodology(
                methodology_id=methodology_data.methodology_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version,
                name=methodology_data.name,
                description=methodology_data.description,
                steps=methodology_data.steps,
            )
            db.add(new_methodology)

    # Relationships
    for relationship_data in domain_data.relationships:
        relationship = (
            db.query(Relationship)
            .filter(
                Relationship.relationship_id == relationship_data.relationship_id,
                Relationship.domain_id == domain_id,
                Relationship.domain_version == new_version,
            )
            .first()
        )

        if relationship:
            # Update existing relationship
            relationship.relationship_type = relationship_data.relationship_type
        else:
            # Add new relationship
            new_relationship = Relationship(
                relationship_id=relationship_data.relationship_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version,
                entity_id_1=relationship_data.entity_id_1,
                entity_type_1=relationship_data.entity_type_1,
                entity_id_2=relationship_data.entity_id_2,
                entity_type_2=relationship_data.entity_type_2,
                relationship_type=relationship_data.relationship_type,
            )
            db.add(new_relationship)

    db.commit()
    db.refresh(new_domain)

    return new_domain


# Adjust get functions to include version filtering
@router.get("/{domain_id}/concepts", response_model=List[ConceptSchema])
def get_concepts_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        version = domain.version

    concepts = (
        db.query(Concept)
        .filter(
            Concept.domain_id == domain_id,
            Concept.domain_version == version,
        )
        .all()
    )

    return concepts


# Similar adjustments for sources
@router.get("/{domain_id}/sources", response_model=List[SourceSchema])
def get_sources_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        version = domain.version

    sources = (
        db.query(Source)
        .filter(
            Source.domain_id == domain_id,
            Source.domain_version == version,
        )
        .all()
    )

    return sources


# Similar adjustments for methodologies
@router.get("/{domain_id}/methodologies", response_model=List[MethodologySchema])
def get_methodologies_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        version = domain.version

    methodologies = (
        db.query(Methodology)
        .filter(
            Methodology.domain_id == domain_id,
            Methodology.domain_version == version,
        )
        .all()
    )

    return methodologies


# Similar adjustments for relationships
@router.get("/{domain_id}/relationships", response_model=List[RelationshipSchema])
def get_relationships_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        version = domain.version

    relationships = (
        db.query(Relationship)
        .filter(
            Relationship.domain_id == domain_id,
            Relationship.domain_version == version,
        )
        .all()
    )

    return relationships


# Update position of an entity
@router.put("/entities/{entity_type}/{entity_id}/position")
def update_entity_position(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get the latest domain version for the entity
    entity = get_entity_by_id_and_type(db, entity_id, entity_type)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Check if the entity belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == entity.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this entity is forbidden"
        )

    db.commit()
    return {"detail": "Position updated"}


# Get domain configuration
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


# Update domain configuration
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


# Utility function to get entity by ID and type
def get_entity_by_id_and_type(db: Session, entity_id: UUID, entity_type: str):
    if entity_type == "concept":
        max_version = (
            db.query(func.max(Concept.domain_version))
            .filter(Concept.concept_id == entity_id)
            .scalar()
        )
        return (
            db.query(Concept)
            .filter(
                Concept.concept_id == entity_id, Concept.domain_version == max_version
            )
            .first()
        )
    elif entity_type == "methodology":
        max_version = (
            db.query(func.max(Methodology.domain_version))
            .filter(Methodology.methodology_id == entity_id)
            .scalar()
        )
        return (
            db.query(Methodology)
            .filter(
                Methodology.methodology_id == entity_id,
                Methodology.domain_version == max_version,
            )
            .first()
        )
    elif entity_type == "source":
        max_version = (
            db.query(func.max(Source.domain_version))
            .filter(Source.source_id == entity_id)
            .scalar()
        )
        return (
            db.query(Source)
            .filter(Source.source_id == entity_id, Source.domain_version == max_version)
            .first()
        )
    else:
        return None
