from pydantic import BaseModel
from typing import Optional, Dict
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


# Schema for domain creation
class DomainCreate(BaseModel):
    domain_name: str
    description: Optional[str] = None


# Schema for domain details
class Domain(BaseModel):
    domain_id: UUID
    domain_name: str
    owner_user_id: UUID
    description: Optional[str]
    created_at: datetime


# Schema for concept details
class Concept(BaseModel):
    concept_id: UUID
    domain_id: UUID
    name: str
    description: Optional[str]
    type: str
    created_at: datetime
    updated_at: datetime


# Schema for source details
class Source(BaseModel):
    source_id: UUID
    domain_id: UUID
    name: str
    source_type: str
    location: str
    description: Optional[str]
    created_at: datetime


# Schema for methodology details
class Methodology(BaseModel):
    methodology_id: UUID
    domain_id: UUID
    name: str
    description: str
    steps: str
    created_at: datetime


# Schema for relationship details
class Relationship(BaseModel):
    relationship_id: UUID
    entity_id_1: UUID
    entity_type_1: str
    entity_id_2: UUID
    entity_type_2: str
    relationship_type: str
    created_at: Optional[datetime] = None


# New: Schema for DomainConfig
class DomainConfig(BaseModel):
    config_id: UUID
    domain_id: UUID
    config_key: str
    config_value: str
    created_at: datetime


# New: Schema for UserConfig
class UserConfig(BaseModel):
    config_id: UUID
    user_id: UUID
    config_key: str
    config_value: str
    created_at: datetime


# UserConfig schema
class UserConfigSchema(BaseModel):
    config_id: UUID
    user_id: UUID
    config_key: str
    config_value: str
    created_at: datetime

    class Config:
        orm_mode = True


# Schema for displaying API Key in the response
class APIKeyResponse(BaseModel):
    api_key_id: UUID
    created_at: datetime
    revoked: datetime | None = None

    class Config:
        orm_mode = True  # This allows compatibility with SQLAlchemy models


# Schema for creating an API Key (response)
class APIKeyCreateResponse(BaseModel):
    api_key: str

    class Config:
        orm_mode = True


# Base schema for creating entities (concepts, sources, methodologies)
class EntityBase(BaseModel):
    name: str
    description: Optional[str] = None
    domain_id: UUID


class EntityCreate(EntityBase):
    type: str  # 'concept', 'methodology', 'source'


class EntityUpdate(BaseModel):
    name: str
    description: Optional[str] = None


class PositionUpdate(BaseModel):
    position: Dict[str, float]  # {'x': float, 'y': float}


# Since we have separate models for Concept, Source, Methodology,
# we'll define an Entity schema that can represent any of them
class Entity(BaseModel):
    id: UUID  # Can be concept_id, source_id, or methodology_id
    domain_id: UUID
    name: str
    description: Optional[str]
    type: str  # 'concept', 'methodology', 'source'
    position_x: Optional[float] = None
    position_y: Optional[float] = None

    class Config:
        orm_mode = True


# Adjusted Relationship schemas
class RelationshipBase(BaseModel):
    entity_id_1: UUID
    entity_type_1: str  # 'concept', 'methodology', 'source'
    entity_id_2: UUID
    entity_type_2: str  # 'concept', 'methodology', 'source'
    relationship_type: str
    domain_id: UUID


class RelationshipCreate(RelationshipBase):
    pass


class RelationshipUpdate(BaseModel):
    relationship_type: str


class Relationship(RelationshipBase):
    relationship_id: UUID
    created_at: datetime

    class Config:
        orm_mode = True


class ConceptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class ConceptUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    position_x: Optional[float] = None
    position_y: Optional[float] = None


# Schemas for Source creation and update
class SourceCreate(BaseModel):
    name: str
    source_type: str
    location: str
    description: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class SourceUpdate(BaseModel):
    name: str
    source_type: str
    location: str
    description: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None


# Schemas for Methodology creation and update
class MethodologyCreate(BaseModel):
    name: str
    description: str
    steps: str
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class MethodologyUpdate(BaseModel):
    name: str
    description: str
    steps: str
    position_x: Optional[float] = None
    position_y: Optional[float] = None


# Schemas for Relationship creation and update
class RelationshipCreate(BaseModel):
    domain_id: UUID
    entity_id_1: UUID
    entity_type_1: str
    entity_id_2: UUID
    entity_type_2: str
    relationship_type: str


class RelationshipUpdate(BaseModel):
    relationship_type: str


# Schema for updating entity position
class PositionUpdate(BaseModel):
    position: Dict[str, float]  # {'x': float, 'y': float}
