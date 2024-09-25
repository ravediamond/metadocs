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


# New Models for Concepts, Sources, Methodologies, and Settings
class Concept(BaseModel):
    concept_id: UUID
    domain_id: UUID
    name: str
    description: Optional[str]
    type: str  # 'definition', 'process', 'methodology', etc.
    created_at: datetime
    updated_at: datetime


class Source(BaseModel):
    source_id: UUID
    domain_id: UUID
    name: str
    source_type: str  # 'table', 'database', 'api'
    location: str
    description: Optional[str]
    created_at: datetime


class Methodology(BaseModel):
    methodology_id: UUID
    domain_id: UUID
    name: str
    description: str
    steps: str  # Detailed steps on how to join sources or get data
    created_at: datetime


class UserSettings(BaseModel):
    user_id: UUID
    setting_key: str
    setting_value: str
    created_at: datetime
    updated_at: datetime


class UserDomainSettings(BaseModel):
    user_id: UUID
    domain_id: UUID
    setting_key: str
    setting_value: str
    created_at: datetime
    updated_at: datetime
