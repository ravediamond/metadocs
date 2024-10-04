from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Role, User, Tenant, UserTenant
from ..models.schemas import Role as RoleSchema, RoleCreate, RoleUpdate
from ..core.permissions import is_admin_user

router = APIRouter()


# Get all roles for a tenant
@router.get("/tenants/{tenant_id}/roles", response_model=List[RoleSchema])
def get_roles(
    tenant_id: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to view roles"
        )

    roles = db.query(Role).filter(Role.tenant_id == tenant_id).all()
    return roles


# Create a new role in a tenant
@router.post("/tenants/{tenant_id}/roles", response_model=RoleSchema)
def create_role(
    tenant_id: UUID,
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to create roles"
        )

    existing_role = (
        db.query(Role)
        .filter(
            Role.role_name == role_data.role_name,
            Role.tenant_id == tenant_id,
        )
        .first()
    )
    if existing_role:
        raise HTTPException(
            status_code=400, detail="Role with this name already exists in this tenant"
        )

    new_role = Role(
        role_id=uuid.uuid4(),
        role_name=role_data.role_name,
        description=role_data.description,
        tenant_id=tenant_id,
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


# Get details of a specific role
@router.get("/tenants/{tenant_id}/roles/{role_id}", response_model=RoleSchema)
def get_role(
    tenant_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to view roles"
        )

    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


# Update a role
@router.put("/tenants/{tenant_id}/roles/{role_id}", response_model=RoleSchema)
def update_role(
    tenant_id: UUID,
    role_id: UUID,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to update roles"
        )

    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role_data.role_name:
        role.role_name = role_data.role_name
    if role_data.description:
        role.description = role_data.description

    db.commit()
    db.refresh(role)
    return role


# Delete a role
@router.delete("/tenants/{tenant_id}/roles/{role_id}")
def delete_role(
    tenant_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to delete roles"
        )

    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    db.delete(role)
    db.commit()
    return {"detail": "Role deleted successfully"}


# Assign a role to a user in a tenant
@router.post("/tenants/{tenant_id}/users/{user_id}/roles/{role_id}")
def assign_role_to_user(
    tenant_id: UUID,
    user_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to assign roles"
        )

    # Verify role exists in tenant
    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify user exists and is part of the tenant
    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not user_tenant:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # Assign the new role
    user_tenant.role_id = role_id
    db.commit()
    return {"detail": "Role assigned to user successfully"}
