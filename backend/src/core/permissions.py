from sqlalchemy.orm import Session
from ..models.models import User, UserRole, Role
from uuid import UUID


def has_permission(
    user: User, domain_id: UUID, required_roles: list, db: Session
) -> bool:
    user_roles = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.user_id, UserRole.domain_id == domain_id)
        .all()
    )
    user_role_names = [
        db.query(Role).filter(Role.role_id == ur.role_id).first().role_name
        for ur in user_roles
    ]
    return any(role in required_roles for role in user_role_names)
