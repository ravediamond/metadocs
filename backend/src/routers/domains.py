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
    DomainVersion,
    User,
    Concept,
    Source,
    Methodology,
    Relationship,
    DomainConfig,
    Role,
    UserRole,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
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
    DomainSaveSchema,
)
from ..core.permissions import has_permission

router = APIRouter()


# Create a new domain and assign 'owner' role to the creator
@router.post("/", response_model=DomainSchema)
def create_domain(
    domain_create: DomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    domain_id = uuid.uuid4()
    new_domain = Domain(
        domain_id=domain_id,
        domain_name=domain_create.domain_name,
        owner_user_id=current_user.user_id,
        description=domain_create.description,
        created_at=func.now(),
    )
    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    # Create the initial domain version
    new_domain_version = DomainVersion(
        domain_id=domain_id,
        version=1,
        created_at=func.now(),
    )
    db.add(new_domain_version)
    db.commit()

    # Assign 'owner' role to the creator
    owner_role = db.query(Role).filter(Role.role_name == "owner").first()
    if not owner_role:
        raise HTTPException(status_code=500, detail="Owner role not found")

    user_role = UserRole(
        user_id=current_user.user_id,
        domain_id=domain_id,
        role_id=owner_role.role_id,
    )
    db.add(user_role)
    db.commit()

    return new_domain


# Get all domains the current user has access to
@router.get("/", response_model=List[DomainSchema])
def get_domains(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Subquery to get the latest version number for each domain
    latest_versions_subq = (
        db.query(
            DomainVersion.domain_id,
            func.max(DomainVersion.version).label("latest_version"),
        )
        .group_by(DomainVersion.domain_id)
        .subquery()
    )

    # Query domains and include latest version number
    domains = (
        db.query(Domain, latest_versions_subq.c.latest_version.label("version"))
        .join(UserRole, UserRole.domain_id == Domain.domain_id)
        .join(
            latest_versions_subq, Domain.domain_id == latest_versions_subq.c.domain_id
        )
        .filter(UserRole.user_id == current_user.user_id)
        .all()
    )

    if not domains:
        raise HTTPException(
            status_code=404, detail="No domains found for the current user"
        )

    # Prepare the response
    result = []
    for domain, version in domains:
        domain_data = {
            "domain_id": domain.domain_id,
            "domain_name": domain.domain_name,
            "description": domain.description,
            "created_at": domain.created_at,
            "version": version,
        }
        result.append(domain_data)

    return result


# Get domain details if the user has access
@router.get("/{domain_id}/details", response_model=DomainDataSchema)
def get_domain_details(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(
        current_user, domain_id, ["owner", "admin", "member", "viewer"], db
    ):
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    domain = db.query(Domain).filter(Domain.domain_id == domain_id).first()

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    if version is None:
        latest_version = (
            db.query(func.max(DomainVersion.version))
            .filter(DomainVersion.domain_id == domain_id)
            .scalar()
        )
        if latest_version is None:
            raise HTTPException(
                status_code=404, detail="No versions found for this domain"
            )
        version = latest_version

    domain_version = (
        db.query(DomainVersion)
        .filter(
            DomainVersion.domain_id == domain_id,
            DomainVersion.version == version,
        )
        .first()
    )

    if not domain_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    concepts = (
        db.query(Concept)
        .filter(Concept.domain_id == domain_id, Concept.domain_version == version)
        .all()
    )

    sources = (
        db.query(Source)
        .filter(Source.domain_id == domain_id, Source.domain_version == version)
        .all()
    )

    methodologies = (
        db.query(Methodology)
        .filter(
            Methodology.domain_id == domain_id, Methodology.domain_version == version
        )
        .all()
    )

    relationships = (
        db.query(Relationship)
        .filter(
            Relationship.domain_id == domain_id, Relationship.domain_version == version
        )
        .all()
    )

    return DomainDataSchema(
        domain_id=domain.domain_id,
        domain_name=domain.domain_name,
        description=domain.description,
        version=version,
        created_at=domain_version.created_at,
        concepts=concepts,
        sources=sources,
        methodologies=methodologies,
        relationships=relationships,
    )


# Save the domain with a new version
@router.post("/{domain_id}/save", response_model=DomainSchema)
def save_domain(
    domain_id: UUID,
    domain_data: DomainSaveSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to save domain"
        )

    domain = db.query(Domain).filter(Domain.domain_id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    latest_version_number = (
        db.query(func.max(DomainVersion.version))
        .filter(DomainVersion.domain_id == domain_id)
        .scalar()
    )
    if latest_version_number is None:
        raise HTTPException(status_code=404, detail="No versions found for this domain")

    new_version_number = latest_version_number + 1

    # Create new domain version
    new_domain_version = DomainVersion(
        domain_id=domain_id,
        version=new_version_number,
        created_at=func.now(),
    )
    db.add(new_domain_version)
    db.commit()

    # Copy existing entities to the new version
    for model in [Concept, Source, Methodology, Relationship]:
        existing_entities = (
            db.query(model)
            .filter(
                model.domain_id == domain_id,
                model.domain_version == latest_version_number,
            )
            .all()
        )
        for entity in existing_entities:
            new_entity_data = {
                column.name: getattr(entity, column.name)
                for column in model.__table__.columns
                if column.name not in ["created_at", "updated_at"]
            }
            new_entity_data["domain_version"] = new_version_number
            new_entity = model(**new_entity_data)
            db.add(new_entity)
    db.commit()

    # Apply updates from domain_data
    # Update or add new concepts
    for concept_data in domain_data.concepts:
        concept = (
            db.query(Concept)
            .filter(
                Concept.concept_id == concept_data.concept_id,
                Concept.domain_id == domain_id,
                Concept.domain_version == new_version_number,
            )
            .first()
        )
        if concept:
            concept.name = concept_data.name
            concept.description = concept_data.description
            concept.type = concept_data.type
            concept.updated_at = func.now()
        else:
            new_concept = Concept(
                concept_id=concept_data.concept_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version_number,
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
                Source.domain_version == new_version_number,
            )
            .first()
        )
        if source:
            source.name = source_data.name
            source.description = source_data.description
            source.source_type = source_data.source_type
            source.location = source_data.location
        else:
            new_source = Source(
                source_id=source_data.source_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version_number,
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
                Methodology.domain_version == new_version_number,
            )
            .first()
        )
        if methodology:
            methodology.name = methodology_data.name
            methodology.description = methodology_data.description
            methodology.steps = methodology_data.steps
        else:
            new_methodology = Methodology(
                methodology_id=methodology_data.methodology_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version_number,
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
                Relationship.domain_version == new_version_number,
            )
            .first()
        )
        if relationship:
            relationship.relationship_type = relationship_data.relationship_type
        else:
            new_relationship = Relationship(
                relationship_id=relationship_data.relationship_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version_number,
                entity_id_1=relationship_data.entity_id_1,
                entity_type_1=relationship_data.entity_type_1,
                entity_id_2=relationship_data.entity_id_2,
                entity_type_2=relationship_data.entity_type_2,
                relationship_type=relationship_data.relationship_type,
            )
            db.add(new_relationship)

    db.commit()
    db.refresh(new_domain_version)

    return domain


# Get concepts for a domain if the user has access
@router.get("/{domain_id}/concepts", response_model=List[ConceptSchema])
def get_concepts_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(
        current_user, domain_id, ["owner", "admin", "member", "viewer"], db
    ):
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        latest_version = (
            db.query(func.max(DomainVersion.version))
            .filter(DomainVersion.domain_id == domain_id)
            .scalar()
        )
        if latest_version is None:
            raise HTTPException(
                status_code=404, detail="No versions found for this domain"
            )
        version = latest_version

    concepts = (
        db.query(Concept)
        .filter(Concept.domain_id == domain_id, Concept.domain_version == version)
        .all()
    )

    return concepts


# Get sources for a domain if the user has access
@router.get("/{domain_id}/sources", response_model=List[SourceSchema])
def get_sources_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(
        current_user, domain_id, ["owner", "admin", "member", "viewer"], db
    ):
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        latest_version = (
            db.query(func.max(DomainVersion.version))
            .filter(DomainVersion.domain_id == domain_id)
            .scalar()
        )
        if latest_version is None:
            raise HTTPException(
                status_code=404, detail="No versions found for this domain"
            )
        version = latest_version

    sources = (
        db.query(Source)
        .filter(Source.domain_id == domain_id, Source.domain_version == version)
        .all()
    )

    return sources


# Get methodologies for a domain if the user has access
@router.get("/{domain_id}/methodologies", response_model=List[MethodologySchema])
def get_methodologies_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(
        current_user, domain_id, ["owner", "admin", "member", "viewer"], db
    ):
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        latest_version = (
            db.query(func.max(DomainVersion.version))
            .filter(DomainVersion.domain_id == domain_id)
            .scalar()
        )
        if latest_version is None:
            raise HTTPException(
                status_code=404, detail="No versions found for this domain"
            )
        version = latest_version

    methodologies = (
        db.query(Methodology)
        .filter(
            Methodology.domain_id == domain_id, Methodology.domain_version == version
        )
        .all()
    )

    return methodologies


# Get relationships for a domain if the user has access
@router.get("/{domain_id}/relationships", response_model=List[RelationshipSchema])
def get_relationships_for_domain(
    domain_id: UUID,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(
        current_user, domain_id, ["owner", "admin", "member", "viewer"], db
    ):
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    if version is None:
        latest_version = (
            db.query(func.max(DomainVersion.version))
            .filter(DomainVersion.domain_id == domain_id)
            .scalar()
        )
        if latest_version is None:
            raise HTTPException(
                status_code=404, detail="No versions found for this domain"
            )
        version = latest_version

    relationships = (
        db.query(Relationship)
        .filter(
            Relationship.domain_id == domain_id, Relationship.domain_version == version
        )
        .all()
    )

    return relationships


# Update the position of an entity if the user has permission
@router.put("/entities/{entity_type}/{entity_id}/position")
def update_entity_position(
    entity_type: str,
    entity_id: UUID,
    position_data: dict,  # Assume position data is passed in request body
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity = get_entity_by_id_and_type(db, entity_id, entity_type)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if not has_permission(
        current_user, entity.domain_id, ["owner", "admin", "member"], db
    ):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to update entity"
        )

    # Update the entity's position here (assuming position fields exist)
    # entity.position_x = position_data.get('x')
    # entity.position_y = position_data.get('y')

    db.commit()
    return {"detail": "Position updated"}


# Get domain configuration if the user has permission
@router.get("/{domain_id}/config", response_model=List[DomainConfigSchema])
def get_domain_config(
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to access config"
        )

    config = db.query(DomainConfig).filter(DomainConfig.domain_id == domain_id).all()
    if not config:
        raise HTTPException(
            status_code=404, detail="No configuration found for this domain"
        )

    return config


# Update domain configuration if the user has permission
@router.put("/{domain_id}/config", response_model=DomainConfigSchema)
def update_domain_config(
    domain_id: UUID,
    config_key: str,
    config_value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to update config"
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
    model = {"concept": Concept, "methodology": Methodology, "source": Source}.get(
        entity_type
    )
    if not model:
        return None
    max_version = (
        db.query(func.max(model.domain_version))
        .filter(getattr(model, f"{entity_type}_id") == entity_id)
        .scalar()
    )
    return (
        db.query(model)
        .filter(
            getattr(model, f"{entity_type}_id") == entity_id,
            model.domain_version == max_version,
        )
        .first()
    )
