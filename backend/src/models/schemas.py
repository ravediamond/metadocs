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


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    name: str
    created_at: datetime


class DomainCreate(BaseModel):
    domain_name: str
    description: Optional[str] = None


class Domain(BaseModel):
    domain_id: UUID
    domain_name: str
    owner_user_id: UUID
    description: Optional[str]
    created_at: datetime


class Concept(BaseModel):
    concept_id: UUID
    domain_id: UUID
    name: str
    description: Optional[str]
    type: str
    created_at: datetime
    updated_at: datetime


class Source(BaseModel):
    source_id: UUID
    domain_id: UUID
    name: str
    source_type: str
    location: str
    description: Optional[str]
    created_at: datetime


class Methodology(BaseModel):
    methodology_id: UUID
    domain_id: UUID
    name: str
    description: str
    steps: str
    created_at: datetime


class Relationship(BaseModel):
    relationship_id: UUID
    entity_id_1: UUID
    entity_type_1: str
    entity_id_2: UUID
    entity_type_2: str
    relationship_type: str
    created_at: Optional[datetime] = None
