from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import (
    Domain,
    User,
    DomainConfig,
    Concept,
    Source,
    Methodology,
    Relationship,
)
from ..models.schemas import (
    Domain as DomainSchema,
    Concept as ConceptSchema,
    ConceptCreate as ConceptCreateSchema,
    ConceptUpdate as ConceptUpdateSchema,
    Source as SourceSchema,
    SourceCreate as SourceCreateSchema,
    SourceUpdate as SourceUpdateSchema,
    Methodology as MethodologySchema,
    MethodologyCreate as MethodologyCreateSchema,
    MethodologyUpdate as MethodologyUpdateSchema,
    Relationship as RelationshipSchema,
    RelationshipCreate as RelationshipCreateSchema,
    RelationshipUpdate as RelationshipUpdateSchema,
    DomainConfig as DomainConfigSchema,
    PositionUpdate as PositionUpdateSchema,
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
            joinedload(Domain.concepts),
            joinedload(Domain.sources),
            joinedload(Domain.methodologies),
            joinedload(Domain.relationships),
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
        .options(joinedload(Domain.concepts))
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )
    return domain.concepts


# Create a new concept
@router.post("/{domain_id}/concepts", response_model=ConceptSchema)
def create_concept(
    domain_id: UUID,
    concept: ConceptCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if domain exists and belongs to the user
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

    new_concept = Concept(
        domain_id=domain_id,
        name=concept.name,
        description=concept.description,
        type=concept.type,
        position_x=concept.position_x,
        position_y=concept.position_y,
    )
    db.add(new_concept)
    db.commit()
    db.refresh(new_concept)
    return new_concept


# Update an existing concept
@router.put("/concepts/{concept_id}", response_model=ConceptSchema)
def update_concept(
    concept_id: UUID,
    concept_update: ConceptUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    concept = db.query(Concept).filter(Concept.concept_id == concept_id).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # Check if the concept belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == concept.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this concept is forbidden"
        )

    concept.name = concept_update.name
    concept.description = concept_update.description
    concept.type = concept_update.type
    db.commit()
    db.refresh(concept)
    return concept


# Delete a concept
@router.delete("/concepts/{concept_id}")
def delete_concept(
    concept_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    concept = db.query(Concept).filter(Concept.concept_id == concept_id).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # Check if the concept belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == concept.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this concept is forbidden"
        )

    db.delete(concept)
    db.commit()
    return {"detail": "Concept deleted"}


# Similar routes for Sources
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
        .options(joinedload(Domain.sources))
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )
    return domain.sources


# Create a new source
@router.post("/{domain_id}/sources", response_model=SourceSchema)
def create_source(
    domain_id: UUID,
    source: SourceCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if domain exists and belongs to the user
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

    new_source = Source(
        domain_id=domain_id,
        name=source.name,
        description=source.description,
        source_type=source.source_type,
        location=source.location,
        position_x=source.position_x,
        position_y=source.position_y,
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source


# Update an existing source
@router.put("/sources/{source_id}", response_model=SourceSchema)
def update_source(
    source_id: UUID,
    source_update: SourceUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = db.query(Source).filter(Source.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Check if the source belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == source.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this source is forbidden"
        )

    source.name = source_update.name
    source.description = source_update.description
    source.source_type = source_update.source_type
    source.location = source_update.location
    db.commit()
    db.refresh(source)
    return source


# Delete a source
@router.delete("/sources/{source_id}")
def delete_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = db.query(Source).filter(Source.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Check if the source belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == source.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this source is forbidden"
        )

    db.delete(source)
    db.commit()
    return {"detail": "Source deleted"}


# Similar routes for Methodologies
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
        .options(joinedload(Domain.methodologies))
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )
    return domain.methodologies


# Create a new methodology
@router.post("/{domain_id}/methodologies", response_model=MethodologySchema)
def create_methodology(
    domain_id: UUID,
    methodology: MethodologyCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if domain exists and belongs to the user
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

    new_methodology = Methodology(
        domain_id=domain_id,
        name=methodology.name,
        description=methodology.description,
        steps=methodology.steps,
        position_x=methodology.position_x,
        position_y=methodology.position_y,
    )
    db.add(new_methodology)
    db.commit()
    db.refresh(new_methodology)
    return new_methodology


# Update an existing methodology
@router.put("/methodologies/{methodology_id}", response_model=MethodologySchema)
def update_methodology(
    methodology_id: UUID,
    methodology_update: MethodologyUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    methodology = (
        db.query(Methodology)
        .filter(Methodology.methodology_id == methodology_id)
        .first()
    )
    if not methodology:
        raise HTTPException(status_code=404, detail="Methodology not found")

    # Check if the methodology belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == methodology.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this methodology is forbidden"
        )

    methodology.name = methodology_update.name
    methodology.description = methodology_update.description
    methodology.steps = methodology_update.steps
    db.commit()
    db.refresh(methodology)
    return methodology


# Delete a methodology
@router.delete("/methodologies/{methodology_id}")
def delete_methodology(
    methodology_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    methodology = (
        db.query(Methodology)
        .filter(Methodology.methodology_id == methodology_id)
        .first()
    )
    if not methodology:
        raise HTTPException(status_code=404, detail="Methodology not found")

    # Check if the methodology belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == methodology.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this methodology is forbidden"
        )

    db.delete(methodology)
    db.commit()
    return {"detail": "Methodology deleted"}


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
        .options(joinedload(Domain.relationships))
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )
    return domain.relationships


# Create a new relationship
@router.post("/relationships", response_model=RelationshipSchema)
def create_relationship(
    relationship: RelationshipCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if domain exists and belongs to the user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == relationship.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    # Validate entities
    entity1 = get_entity_by_id_and_type(
        db, relationship.entity_id_1, relationship.entity_type_1
    )
    entity2 = get_entity_by_id_and_type(
        db, relationship.entity_id_2, relationship.entity_type_2
    )

    if not entity1 or not entity2:
        raise HTTPException(status_code=404, detail="One or both entities not found")

    if entity1.domain_id != domain.domain_id or entity2.domain_id != domain.domain_id:
        raise HTTPException(
            status_code=403, detail="Entities must belong to the same domain"
        )

    new_relationship = Relationship(
        domain_id=relationship.domain_id,
        entity_id_1=relationship.entity_id_1,
        entity_type_1=relationship.entity_type_1,
        entity_id_2=relationship.entity_id_2,
        entity_type_2=relationship.entity_type_2,
        relationship_type=relationship.relationship_type,
    )
    db.add(new_relationship)
    db.commit()
    db.refresh(new_relationship)
    return new_relationship


# Update an existing relationship
@router.put("/relationships/{relationship_id}", response_model=RelationshipSchema)
def update_relationship(
    relationship_id: UUID,
    relationship_update: RelationshipUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    relationship = (
        db.query(Relationship)
        .filter(Relationship.relationship_id == relationship_id)
        .first()
    )
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")

    # Check if the relationship belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == relationship.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this relationship is forbidden"
        )

    relationship.relationship_type = relationship_update.relationship_type
    db.commit()
    db.refresh(relationship)
    return relationship


# Delete a relationship
@router.delete("/relationships/{relationship_id}")
def delete_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    relationship = (
        db.query(Relationship)
        .filter(Relationship.relationship_id == relationship_id)
        .first()
    )
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")

    # Check if the relationship belongs to a domain owned by the current user
    domain = (
        db.query(Domain)
        .filter(
            Domain.domain_id == relationship.domain_id,
            Domain.owner_user_id == current_user.user_id,
        )
        .first()
    )
    if not domain:
        raise HTTPException(
            status_code=403, detail="Access to this relationship is forbidden"
        )

    db.delete(relationship)
    db.commit()
    return {"detail": "Relationship deleted"}


# Update position of an entity
@router.put("/entities/{entity_type}/{entity_id}/position")
def update_entity_position(
    entity_type: str,
    entity_id: UUID,
    position_update: PositionUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    entity.position_x = position_update.position.get("x")
    entity.position_y = position_update.position.get("y")

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
        return db.query(Concept).filter(Concept.concept_id == entity_id).first()
    elif entity_type == "methodology":
        return (
            db.query(Methodology)
            .filter(Methodology.methodology_id == entity_id)
            .first()
        )
    elif entity_type == "source":
        return db.query(Source).filter(Source.source_id == entity_id).first()
    else:
        return None
