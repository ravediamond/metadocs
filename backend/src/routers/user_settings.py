from fastapi import APIRouter, Depends, HTTPException
from typing import List

from src.auth.jwt import get_current_user
from src.models.schemas import UserSettings
from src.db.user_settings import get_user_settings, create_or_update_user_setting

router = APIRouter()


# Route to get user settings
@router.get("/", response_model=List[UserSettings])
async def get_settings(current_user=Depends(get_current_user)):
    user_id = current_user["sub"]

    settings = get_user_settings(user_id)

    if not settings:
        raise HTTPException(status_code=404, detail="No settings found for the user")

    return settings


# Route to create or update a user setting
@router.post("/", response_model=UserSettings)
async def create_or_update_setting(
    setting_data: UserSettings, current_user=Depends(get_current_user)
):
    user_id = current_user["sub"]

    updated_setting = create_or_update_user_setting(
        user_id=user_id,
        setting_key=setting_data.setting_key,
        setting_value=setting_data.setting_value,
    )

    if not updated_setting:
        raise HTTPException(status_code=500, detail="Failed to update user setting")

    return updated_setting
