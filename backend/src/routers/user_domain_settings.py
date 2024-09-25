from fastapi import APIRouter, Depends, HTTPException
from typing import List

from src.auth.jwt import get_current_user
from src.models.schemas import UserDomainSettings
from src.db.user_domain_settings import (
    get_user_domain_settings,
    create_or_update_user_domain_setting,
)

router = APIRouter()


# Route to get domain-specific settings for the current user
@router.get("/{domain_id}", response_model=List[UserDomainSettings])
async def get_domain_settings(domain_id: str, current_user=Depends(get_current_user)):
    user_id = current_user["sub"]

    settings = get_user_domain_settings(user_id=user_id, domain_id=domain_id)

    if not settings:
        raise HTTPException(
            status_code=404, detail="No domain-specific settings found for this user"
        )

    return settings


# Route to create or update a user domain-specific setting
@router.post("/", response_model=UserDomainSettings)
async def create_or_update_domain_setting(
    domain_id: str,
    setting_data: UserDomainSettings,
    current_user=Depends(get_current_user),
):
    user_id = current_user["sub"]

    updated_setting = create_or_update_user_domain_setting(
        user_id=user_id,
        domain_id=domain_id,
        setting_key=setting_data.setting_key,
        setting_value=setting_data.setting_value,
    )

    if not updated_setting:
        raise HTTPException(
            status_code=500, detail="Failed to update domain-specific setting"
        )

    return updated_setting
