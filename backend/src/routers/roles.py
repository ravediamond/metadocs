from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Role, UserRole, User, Domain
from ..models.schemas import UserRoleCreate, UserRole as UserRoleSchema
from ..core.permissions import has_permission

router = APIRouter()


@router.post(
    "/domains/{domain_id}/users/{user_id}/roles", response_model=UserRoleSchema
)
def assign_role_to_user(
    domain_id: UUID,
    user_id: UUID,
    user_role_create: UserRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check if current_user has 'owner' role in the domain
    if not has_permission(current_user, domain_id, ["owner"], db):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check if user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if domain exists
    domain = db.query(Domain).filter(Domain.domain_id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Check if role exists
    role = db.query(Role).filter(Role.role_id == user_role_create.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Assign role
    user_role = UserRole(user_id=user_id, domain_id=domain_id, role_id=role.role_id)
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    return user_role
