from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Domain, User, UserConfig
from ..models.schemas import Domain as DomainSchema, UserResponse, UserConfigSchema

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users/{user_id}/domains", response_model=List[DomainSchema])
def get_domains_for_user(user_id: UUID, db: Session = Depends(get_db)):
    domains = db.query(Domain).filter(Domain.owner_user_id == user_id).all()
    if not domains:
        raise HTTPException(status_code=404, detail="No domains found for this user")
    return domains


# New: Get user configuration
@router.get("/users/{user_id}/config", response_model=List[UserConfigSchema])
def get_user_config(user_id: UUID, db: Session = Depends(get_db)):
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).all()
    if not config:
        raise HTTPException(
            status_code=404, detail="No configuration found for this user"
        )
    return config


# New: Update user configuration
@router.put("/users/{user_id}/config", response_model=UserConfigSchema)
def update_user_config(
    user_id: UUID, config_key: str, config_value: str, db: Session = Depends(get_db)
):
    user_config = (
        db.query(UserConfig)
        .filter(UserConfig.user_id == user_id, UserConfig.config_key == config_key)
        .first()
    )

    if not user_config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    user_config.config_value = config_value
    db.commit()
    db.refresh(user_config)
    return user_config
