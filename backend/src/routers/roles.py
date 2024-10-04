from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Role, User, Tenant
from ..models.schemas import Role as RoleSchema, RoleCreate, RoleUpdate
from ..core.permissions import is_admin_user

router = APIRouter()


# Get all roles
@router.get("/", response_model=List[RoleSchema])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin_user(current_user, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to view roles"
        )

    roles = db.query(Role).filter(Role.tenant_id == current_user.tenant_id).all()
    return roles


# Create a new role
@router.post("/", response_model=RoleSchema)
def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin_user(current_user, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to create roles"
        )

    existing_role = (
        db.query(Role)
        .filter(
            Role.role_name == role_data.role_name,
            Role.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if existing_role:
        raise HTTPException(
            status_code=400, detail="Role with this name already exists"
        )

    new_role = Role(
        role_id=uuid.uuid4(),
        role_name=role_data.role_name,
        description=role_data.description,
        tenant_id=current_user.tenant_id,
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


# Get details of a specific role
@router.get("/{role_id}", response_model=RoleSchema)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin_user(current_user, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to view roles"
        )

    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == current_user.tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


# Update a role
@router.put("/{role_id}", response_model=RoleSchema)
def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin_user(current_user, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to update roles"
        )

    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == current_user.tenant_id)
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
@router.delete("/{role_id}")
def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin_user(current_user, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to delete roles"
        )

    role = (
        db.query(Role)
        .filter(Role.role_id == role_id, Role.tenant_id == current_user.tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    db.delete(role)
    db.commit()
    return {"detail": "Role deleted successfully"}
