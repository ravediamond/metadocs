from uuid import UUID
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
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
    UserTenant,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainDataSchema,
    DomainSaveSchema,
    UserRoleCreate,
    UserRoleResponse,
    DomainConfigSchema,
)
from ..core.permissions import has_permission
from ..core.utils import generate_uuid

router = APIRouter()


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


# Get domain details if the user has access
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

    concepts = (
        db.query(Concept)
        .filter(
            Concept.domain_id == domain_id,
            Concept.domain_version == version,
            Concept.tenant_id == tenant_id,
        )
        .all()
    )

    sources = (
        db.query(Source)
        .filter(
            Source.domain_id == domain_id,
            Source.domain_version == version,
            Source.tenant_id == tenant_id,
        )
        .all()
    )

    methodologies = (
        db.query(Methodology)
        .filter(
            Methodology.domain_id == domain_id,
            Methodology.domain_version == version,
            Methodology.tenant_id == tenant_id,
        )
        .all()
    )

    relationships = (
        db.query(Relationship)
        .filter(
            Relationship.domain_id == domain_id,
            Relationship.domain_version == version,
            Relationship.tenant_id == tenant_id,
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
        concepts=concepts,
        sources=sources,
        methodologies=methodologies,
        relationships=relationships,
    )


# Save the domain with a new version
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

    # Copy existing entities to the new version
    for model in [Concept, Source, Methodology, Relationship]:
        existing_entities = (
            db.query(model)
            .filter(
                model.domain_id == domain_id,
                model.domain_version == latest_version_number,
                model.tenant_id == tenant_id,
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
            new_entity_data["tenant_id"] = tenant_id
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
                Concept.tenant_id == tenant_id,
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
                tenant_id=tenant_id,
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
                Source.tenant_id == tenant_id,
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
                tenant_id=tenant_id,
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
                Methodology.tenant_id == tenant_id,
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
                tenant_id=tenant_id,
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
                Relationship.tenant_id == tenant_id,
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
                tenant_id=tenant_id,
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


# Additional endpoints (concepts, sources, methodologies, relationships) can be updated similarly.


# Utility function to get entity by ID and type
def get_entity_by_id_and_type(
    db: Session, entity_id: UUID, entity_type: str, tenant_id: UUID
):
    model = {"concept": Concept, "methodology": Methodology, "source": Source}.get(
        entity_type.lower()
    )
    if not model:
        return None
    max_version = (
        db.query(func.max(model.domain_version))
        .filter(
            getattr(model, f"{entity_type}_id") == entity_id,
            model.tenant_id == tenant_id,
        )
        .scalar()
    )
    return (
        db.query(model)
        .filter(
            getattr(model, f"{entity_type}_id") == entity_id,
            model.domain_version == max_version,
            model.tenant_id == tenant_id,
        )
        .first()
    )


# Assign or update role to a user in a domain
@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/users/{user_id}/roles",
    response_model=UserRoleResponse,
)
def assign_or_update_role_to_user(
    tenant_id: UUID,
    domain_id: UUID,
    user_id: UUID,
    user_role_create: UserRoleCreate,  # Expect role_name in the request body
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify current user has 'owner' or 'admin' role in the domain
    if not has_permission(current_user, tenant_id, domain_id, ["owner", "admin"], db):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check if user exists and belongs to the tenant
    target_user_tenant = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id)
        .first()
    )
    if not target_user_tenant:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # Check if role exists by role_name and get the role_id
    role = (
        db.query(Role)
        .filter(
            Role.role_name == user_role_create.role_name, Role.tenant_id == tenant_id
        )
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check if the user already has a role in the domain
    existing_user_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.domain_id == domain_id)
        .first()
    )

    if existing_user_role:
        # Update the role
        existing_user_role.role_id = role.role_id
        db.commit()
        db.refresh(existing_user_role)
    else:
        # Assign a new role
        new_user_role = UserRole(
            user_id=user_id,
            domain_id=domain_id,
            role_id=role.role_id,
        )
        db.add(new_user_role)
        db.commit()
        db.refresh(new_user_role)
        existing_user_role = new_user_role

    return UserRoleResponse(
        user_id=existing_user_role.user_id,
        domain_id=existing_user_role.domain_id,
        role_name=role.role_name,
        email=target_user_tenant.user.email,
        name=target_user_tenant.user.name,
    )


# Revoke role from user in a domain
@router.delete(
    "/tenants/{tenant_id}/domains/{domain_id}/users/{user_id}/roles/{role_name}"
)
def revoke_role_from_user(
    tenant_id: UUID,
    domain_id: UUID,
    user_id: UUID,
    role_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has 'owner' or 'admin' role in the domain
    if not has_permission(current_user, tenant_id, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to revoke roles"
        )

    # Get the role object
    role = (
        db.query(Role)
        .filter(Role.role_name == role_name, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Find the user role association
    user_role = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_id,
            UserRole.domain_id == domain_id,
            UserRole.role_id == role.role_id,
        )
        .first()
    )
    if not user_role:
        raise HTTPException(
            status_code=404, detail="User does not have this role in the domain"
        )

    # Revoke the role
    db.delete(user_role)
    db.commit()
    return {"detail": "Role revoked successfully"}


# List users in a domain
@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/users",
    response_model=List[UserRoleResponse],
)
def list_users_in_domain(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify user has permission to view users in the domain
    if not has_permission(
        current_user, tenant_id, domain_id, ["owner", "admin", "Member"], db
    ):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to view users"
        )

    user_roles = (
        db.query(
            UserRole.user_id,
            UserRole.domain_id,
            Role.role_name,
            User.email,
            User.name,
        )
        .join(Role, UserRole.role_id == Role.role_id)
        .join(User, User.user_id == UserRole.user_id)
        .filter(UserRole.domain_id == domain_id)
        .all()
    )

    result = [
        {
            "user_id": ur.user_id,
            "domain_id": ur.domain_id,
            "role_name": ur.role_name,
            "email": ur.email,
            "name": ur.name,
        }
        for ur in user_roles
    ]

    return result


# Get domain configuration
@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/config",
    response_model=List[DomainConfigSchema],
)
def get_domain_config(
    tenant_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify user has permission to access domain config
    if not has_permission(current_user, tenant_id, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to access config"
        )

    config = (
        db.query(DomainConfig)
        .filter(
            DomainConfig.domain_id == domain_id,
            DomainConfig.tenant_id == tenant_id,
        )
        .all()
    )

    return config


# Update domain configuration
@router.put(
    "/tenants/{tenant_id}/domains/{domain_id}/config",
    response_model=DomainConfigSchema,
)
def update_domain_config(
    tenant_id: UUID,
    domain_id: UUID,
    config_key: str = Query(...),
    config_value: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify user has permission to update domain config
    if not has_permission(current_user, tenant_id, domain_id, ["owner", "admin"], db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to update config"
        )

    domain_config = (
        db.query(DomainConfig)
        .filter(
            DomainConfig.domain_id == domain_id,
            DomainConfig.config_key == config_key,
            DomainConfig.tenant_id == tenant_id,
        )
        .first()
    )

    if not domain_config:
        # Create new config entry
        domain_config = DomainConfig(
            config_id=uuid.uuid4(),
            domain_id=domain_id,
            tenant_id=tenant_id,
            config_key=config_key,
            config_value=config_value,
        )
        db.add(domain_config)
    else:
        domain_config.config_value = config_value

    db.commit()
    db.refresh(domain_config)
    return domain_config
