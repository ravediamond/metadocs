from uuid import UUID
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.sql import text

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import (
    Domain,
    DomainVersion,
    User,
    Entity,
    RelationshipEdge,
    Role,
    UserRole,
    UserTenant,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainDataSchema,
    DomainSaveSchema,
)
from ..core.permissions import has_permission

router = APIRouter()


# Function to create graph in Apache AGE
def create_graph_in_age(session: Session, domain_id: UUID, version: int):
    graph_name = f"graph_{domain_id}_{version}"
    create_graph_query = text(f"SELECT create_graph(:graph_name);")
    session.execute(create_graph_query, {"graph_name": graph_name})


# Create a new domain and assign 'owner' role to the creator
@router.post("/tenants/{tenant_id}/domains", response_model=DomainSchema)
def create_domain(
    tenant_id: UUID,
    domain_create: DomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user belongs to the tenant
    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not user_tenant:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    domain_id = uuid.uuid4()

    # Create new domain
    new_domain = Domain(
        domain_id=domain_id,
        domain_name=domain_create.domain_name,
        owner_user_id=current_user.user_id,
        description=domain_create.description,
        created_at=func.now(),
        tenant_id=tenant_id,
    )
    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    # Create the initial domain version
    new_domain_version = DomainVersion(
        domain_id=domain_id,
        version=1,
        created_at=func.now(),
        tenant_id=tenant_id,
    )
    db.add(new_domain_version)
    db.commit()

    # Create the graph in Apache AGE for this domain version
    create_graph_in_age(db, domain_id, 1)

    # Assign 'owner' role to the creator in the domain
    owner_role = (
        db.query(Role)
        .filter(Role.role_name == "owner", Role.tenant_id == tenant_id)
        .first()
    )
    if not owner_role:
        # Create the 'owner' role if it doesn't exist
        owner_role = Role(
            role_id=uuid.uuid4(),
            role_name="owner",
            description="Domain owner with full permissions",
            tenant_id=tenant_id,
        )
        db.add(owner_role)
        db.commit()
        db.refresh(owner_role)

    user_role = UserRole(
        user_id=current_user.user_id,
        domain_id=domain_id,
        role_id=owner_role.role_id,
    )
    db.add(user_role)
    db.commit()

    return new_domain


# Get all domains the current user has access to in a tenant
@router.get("/tenants/{tenant_id}/domains", response_model=List[DomainSchema])
def get_domains(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user belongs to the tenant
    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not user_tenant:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

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
        .filter(
            UserRole.user_id == current_user.user_id,
            Domain.tenant_id == tenant_id,
        )
        .all()
    )

    # Prepare the response
    result = []
    for domain, version in domains:
        domain_data = {
            "domain_id": domain.domain_id,
            "domain_name": domain.domain_name,
            "description": domain.description,
            "tenant_id": domain.tenant_id,
            "created_at": domain.created_at,
            "version": version,
        }
        result.append(domain_data)

    return result


# Get domain details with entities and relationships (graph details)
@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/details", response_model=DomainDataSchema
)
def get_domain_details(
    tenant_id: UUID,
    domain_id: UUID,
    version: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify user has permission to access the domain
    if not has_permission(
        current_user,
        tenant_id,
        domain_id,
        ["owner", "admin", "member", "viewer"],
        db,
    ):
        raise HTTPException(
            status_code=403, detail="Access to this domain is forbidden"
        )

    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    if version is None:
        latest_version = (
            db.query(func.max(DomainVersion.version))
            .filter(
                DomainVersion.domain_id == domain_id,
                DomainVersion.tenant_id == tenant_id,
            )
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
            DomainVersion.tenant_id == tenant_id,
        )
        .first()
    )

    if not domain_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    entities = (
        db.query(Entity)
        .filter(
            Entity.domain_id == domain_id,
            Entity.domain_version == version,
            Entity.tenant_id == tenant_id,
        )
        .all()
    )

    relationships = (
        db.query(RelationshipEdge)
        .filter(
            RelationshipEdge.domain_id == domain_id,
            RelationshipEdge.domain_version == version,
            RelationshipEdge.tenant_id == tenant_id,
        )
        .all()
    )

    return DomainDataSchema(
        domain_id=domain.domain_id,
        domain_name=domain.domain_name,
        description=domain.description,
        tenant_id=tenant_id,
        version=version,
        created_at=domain_version.created_at,
        concepts=entities,  # Entities now represent the concepts
        relationships=relationships,  # Relationship edges now represent relationships
    )


# Save the domain with a new version (graph saving)
@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/save", response_model=DomainSchema
)
def save_domain(
    tenant_id: UUID,
    domain_id: UUID,
    domain_data: DomainSaveSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify user has permission to save the domain
    if not has_permission(current_user, tenant_id, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to save domain"
        )

    domain = (
        db.query(Domain)
        .filter(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    latest_version_number = (
        db.query(func.max(DomainVersion.version))
        .filter(
            DomainVersion.domain_id == domain_id, DomainVersion.tenant_id == tenant_id
        )
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
        tenant_id=tenant_id,
    )
    db.add(new_domain_version)
    db.commit()

    # Create a new graph for this domain version
    create_graph_in_age(db, domain_id, new_version_number)

    # Copy existing entities and relationships to the new version
    for model in [Entity, RelationshipEdge]:
        existing_items = (
            db.query(model)
            .filter(
                model.domain_id == domain_id,
                model.domain_version == latest_version_number,
                model.tenant_id == tenant_id,
            )
            .all()
        )
        for item in existing_items:
            new_item_data = {
                column.name: getattr(item, column.name)
                for column in model.__table__.columns
                if column.name not in ["created_at", "updated_at"]
            }
            new_item_data["domain_version"] = new_version_number
            new_item = model(**new_item_data)
            db.add(new_item)
    db.commit()

    # Apply updates from domain_data
    # Entities
    for (
        entity_data
    ) in domain_data.concepts:  # Assuming the front-end still sends 'concepts' data
        entity = (
            db.query(Entity)
            .filter(
                Entity.entity_id == entity_data.concept_id,
                Entity.domain_id == domain_id,
                Entity.domain_version == new_version_number,
                Entity.tenant_id == tenant_id,
            )
            .first()
        )
        if entity:
            entity.name = entity_data.name
            entity.description = entity_data.description
            entity.entity_type = entity_data.type
        else:
            new_entity = Entity(
                entity_id=entity_data.concept_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version_number,
                tenant_id=tenant_id,
                name=entity_data.name,
                description=entity_data.description,
                entity_type=entity_data.type,
            )
            db.add(new_entity)

    # Relationships (edges)
    for relationship_data in domain_data.relationships:
        relationship = (
            db.query(RelationshipEdge)
            .filter(
                RelationshipEdge.edge_id == relationship_data.relationship_id,
                RelationshipEdge.domain_id == domain_id,
                RelationshipEdge.domain_version == new_version_number,
                RelationshipEdge.tenant_id == tenant_id,
            )
            .first()
        )
        if relationship:
            relationship.relationship_type = relationship_data.relationship_type
        else:
            new_relationship = RelationshipEdge(
                edge_id=relationship_data.relationship_id or uuid.uuid4(),
                domain_id=domain_id,
                domain_version=new_version_number,
                tenant_id=tenant_id,
                from_entity_id=relationship_data.entity_id_1,
                to_entity_id=relationship_data.entity_id_2,
                relationship_type=relationship_data.relationship_type,
            )
            db.add(new_relationship)

    db.commit()
    db.refresh(new_domain_version)

    return domain
