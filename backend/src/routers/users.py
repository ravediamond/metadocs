from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import Domain, User
from ..models.schemas import Domain as DomainSchema, UserResponse

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
