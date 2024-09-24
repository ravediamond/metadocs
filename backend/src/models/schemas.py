from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    name: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    created_at: datetime


class DomainCreate(BaseModel):
    domain_name: str
    description: Optional[str] = None


class User(BaseModel):
    user_id: str
    email: str
    hashed_password: str
    name: str
    created_at: datetime


class Domain(BaseModel):
    domain_id: UUID
    domain_name: str
    owner_user_id: UUID
    description: Optional[str]
    created_at: datetime
