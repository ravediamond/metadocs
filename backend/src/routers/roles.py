from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Role, User, Tenant, UserTenant, UserRole
from ..models.schemas import (
    Role as RoleSchema,
    RoleCreate,
    RoleUpdate,
    UserRoleCreate,
    UserRoleResponse,
)
from ..core.permissions import is_admin_user
from ..core.permissions import has_permission

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
