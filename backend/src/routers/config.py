from uuid import UUID
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import User, DomainConfig, UserConfig, APIKey, UserTenant
from ..models.schemas import (
    Domain as DomainSchema,
    DomainConfigSchema,
    UserConfigSchema,
    APIKeyResponse,
    APIKeyCreateResponse,
)
from ..core.permissions import has_permission
from ..core.utils import generate_uuid
from ..core.permissions import is_admin_user
from ..core.utils import generate_api_key

router = APIRouter()


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
