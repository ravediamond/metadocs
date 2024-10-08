from sqlalchemy.orm import Session
from ..models.models import User, UserRole, Role
from uuid import UUID
from .database import get_db
from ..models.models import UserRole, Role


def has_permission(
    user: User, tenant_id: UUID, domain_id: UUID, required_roles: list, db: Session
) -> bool:
    # Fetch all roles assigned to the user in the given tenant and domain
    user_roles = (
        db.query(UserRole)
        .join(Role, UserRole.role_id == Role.role_id)
        .filter(
            UserRole.user_id == user.user_id,
            UserRole.domain_id == domain_id,
            Role.tenant_id == tenant_id,  # Role must belong to the same tenant
        )
        .all()
    )

    # Get role names of the user for comparison
    user_role_names = [ur.role.role_name for ur in user_roles]

    # Check if any of the required roles match the user's roles
    return any(role in required_roles for role in user_role_names)


def is_admin_user(current_user: User, tenant_id: UUID, db: Session) -> bool:
    # Check if the user has either the 'admin' or 'owner' role for the specified tenant
    user_role = (
        db.query(UserRole)
        .join(Role, UserRole.role_id == Role.role_id)
        .filter(
            UserRole.user_id == current_user.user_id,
            Role.role_name.in_(["admin", "owner"]),  # Check for both admin and owner
            Role.tenant_id == tenant_id,  # Ensure it's for the current tenant
        )
        .first()
    )

    return user_role is not None
