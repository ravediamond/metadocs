from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import uuid
from sqlalchemy.sql import func
from datetime import datetime

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import (
    Domain,
    User,
    UserConfig,
    APIKey,
    UserRole,
    Role,
    UserTenant,
    Tenant,
    Invitation,
)
from ..models.schemas import (
    Domain as DomainSchema,
    UserResponse,
    UserConfigSchema,
    APIKeyResponse,
    APIKeyCreateResponse,
    Role as RoleSchema,
    UserRoleCreate,
    UserRole as UserRoleSchema,
    UserRoleResponse,
    InvitationResponse,
    InvitationCreate,
)
from ..core.permissions import is_admin_user
from ..core.utils import generate_api_key

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.get(
    "/tenants/{tenant_id}/users/{user_id}/domains", response_model=List[DomainSchema]
)
def get_domains_for_user(
    tenant_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
    current_user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not current_user_tenant:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Check if the target user belongs to the tenant
    target_user_tenant = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id)
        .first()
    )
    if not target_user_tenant:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # Get domains owned by the user in the tenant
    domains = (
        db.query(Domain)
        .filter(
            Domain.owner_user_id == user_id,
            Domain.tenant_id == tenant_id,
        )
        .all()
    )

    return domains


# Get user configuration
@router.get(
    "/tenants/{tenant_id}/users/{user_id}/config",
    response_model=List[UserConfigSchema],
)
def get_user_config(
    tenant_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
    current_user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not current_user_tenant:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Only the user or an admin can access the configuration
    if current_user.user_id != user_id and not is_admin_user(
        current_user, tenant_id, db
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    config = (
        db.query(UserConfig)
        .filter(
            UserConfig.user_id == user_id,
            UserConfig.tenant_id == tenant_id,
        )
        .all()
    )

    return config


# Update user configuration
@router.put(
    "/tenants/{tenant_id}/users/{user_id}/config", response_model=UserConfigSchema
)
def update_user_config(
    tenant_id: UUID,
    user_id: UUID,
    config_key: str,
    config_value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
    current_user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not current_user_tenant:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Only the user or an admin can update the configuration
    if current_user.user_id != user_id and not is_admin_user(
        current_user, tenant_id, db
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user_config = (
        db.query(UserConfig)
        .filter(
            UserConfig.user_id == user_id,
            UserConfig.config_key == config_key,
            UserConfig.tenant_id == tenant_id,
        )
        .first()
    )

    if not user_config:
        # Create new config
        user_config = UserConfig(
            config_id=uuid.uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            config_key=config_key,
            config_value=config_value,
        )
        db.add(user_config)
    else:
        user_config.config_value = config_value

    db.commit()
    db.refresh(user_config)
    return user_config


@router.get("/me/api-keys", response_model=List[APIKeyResponse])
def get_api_keys(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Get all API keys for the user across all tenants
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.user_id).all()
    return api_keys


# Create a new API key for the current user in a tenant
@router.post("/tenants/{tenant_id}/me/api-keys", response_model=APIKeyCreateResponse)
def create_api_key(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
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

    api_key = APIKey(
        api_key_id=uuid.uuid4(),
        api_key=generate_api_key(),
        user_id=current_user.user_id,
        tenant_id=tenant_id,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {"api_key": api_key.api_key}


# Revoke an existing API key
@router.delete("/tenants/{tenant_id}/me/api-keys/{api_key_id}")
def revoke_api_key(
    tenant_id: UUID,
    api_key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
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

    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.api_key_id == api_key_id,
            APIKey.user_id == current_user.user_id,
            APIKey.tenant_id == tenant_id,
        )
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.revoked = func.now()
    db.commit()
    return {"message": "API key revoked"}


@router.get(
    "/tenants/{tenant_id}/users/{user_id}/roles", response_model=List[RoleSchema]
)
def get_user_roles(
    tenant_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print(f"Fetching roles for user {user_id} in tenant {tenant_id}")

    # Verify current user has access to the tenant
    current_user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not current_user_tenant:
        print("Current user has no access to this tenant.")
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Only the user or an admin can view roles
    if current_user.user_id != user_id and not is_admin_user(
        current_user, tenant_id, db
    ):
        print("User lacks sufficient permissions.")
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Get the user's tenant membership record
    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not user_tenant:
        print(f"User {user_id} not found in tenant {tenant_id}")
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    print(f"UserTenant record: {user_tenant}")

    # Fetch the user's role in the tenant
    role = (
        db.query(Role)
        .filter(
            Role.role_id == user_tenant.role_id,
            Role.tenant_id == tenant_id,
        )
        .first()
    )

    if not role:
        print(f"Role with ID {user_tenant.role_id} not found in tenant {tenant_id}")
        raise HTTPException(status_code=404, detail="Role not found")

    print(f"Returning role: {role}")

    return [role]


# List all users in a tenant
@router.get("/tenants/{tenant_id}/users", response_model=List[UserResponse])
def list_users_in_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to view users"
        )

    user_tenants = db.query(UserTenant).filter(UserTenant.tenant_id == tenant_id).all()

    users = []
    for ut in user_tenants:
        user = db.query(User).filter(User.user_id == ut.user_id).first()
        if user:
            users.append(user)

    return users


# Remove a user from a tenant
@router.delete("/tenants/{tenant_id}/users/{user_id}")
def remove_user_from_tenant(
    tenant_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has admin access to the tenant
    if not is_admin_user(current_user, tenant_id, db):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to remove users"
        )

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

    db.delete(user_tenant)
    db.commit()
    return {"detail": "User removed from tenant successfully"}


# Create a new invitation
@router.post("/tenants/{tenant_id}/invite", response_model=InvitationResponse)
def invite_user(
    tenant_id: UUID,
    invitation: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
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

    # Check if the invitee already exists in the tenant
    invitee_exists = (
        db.query(User).filter(User.email == invitation.invitee_email).first()
    )
    if invitee_exists:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create the invitation
    new_invitation = Invitation(
        inviter_user_id=current_user.user_id,
        invitee_email=invitation.invitee_email,
        tenant_id=tenant_id,
        domain_id=invitation.domain_id,
        expires_at=invitation.expires_at,
    )
    db.add(new_invitation)
    db.commit()
    db.refresh(new_invitation)

    # Here you could trigger an email sending process to the invitee
    return new_invitation


# Get all invitations for a tenant
@router.get("/tenants/{tenant_id}/invitations", response_model=List[InvitationResponse])
def list_invitations(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current user has access to the tenant
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

    invitations = db.query(Invitation).filter(Invitation.tenant_id == tenant_id).all()
    return invitations


@router.post("/invitations/{invitation_id}/accept")
def accept_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invitation = (
        db.query(Invitation).filter(Invitation.invitation_id == invitation_id).first()
    )

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.invitee_email != current_user.email:
        raise HTTPException(
            status_code=403, detail="You are not authorized to accept this invitation"
        )

    # Check if role_id is provided by the invitation, otherwise use a default role
    default_role = (
        db.query(Role)
        .filter(Role.tenant_id == invitation.tenant_id, Role.role_name == "User")
        .first()
    )
    if not default_role:
        raise HTTPException(status_code=400, detail="Default role for tenant not found")

    # Assign invitee to the tenant with the specified role or default role
    user_tenant = UserTenant(
        user_id=current_user.user_id,
        tenant_id=invitation.tenant_id,
        role_id=default_role.role_id,  # Use default role or from invitation
    )
    db.add(user_tenant)

    # Mark invitation as accepted
    invitation.status = "accepted"
    invitation.accepted_at = func.now()
    db.commit()

    return {"message": "Invitation accepted and user added to the tenant"}


# Reject an invitation
@router.post("/invitations/{invitation_id}/reject")
def reject_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invitation = (
        db.query(Invitation).filter(Invitation.invitation_id == invitation_id).first()
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.invitee_email != current_user.email:
        raise HTTPException(
            status_code=403, detail="You are not authorized to reject this invitation"
        )

    # Update the invitation status
    invitation.status = "rejected"
    db.commit()
    return {"message": "Invitation rejected"}
