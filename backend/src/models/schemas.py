from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


# Tenant Schemas
class TenantBase(BaseModel):
    tenant_name: str


class TenantResponse(TenantBase):
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


# API Key Schemas
class APIKeyBase(BaseModel):
    api_key_id: UUID
    api_key: str
    tenant_id: UUID
    created_at: datetime
    revoked: Optional[datetime]


class APIKeyResponse(APIKeyBase):
    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    api_key: str


# User Config Schemas
class UserConfigSchema(BaseModel):
    config_id: UUID
    user_id: UUID
    tenant_id: UUID
    config_key: str
    config_value: str
    created_at: datetime

    class Config:
        from_attributes = True


# Domain Schemas
class DomainBase(BaseModel):
    domain_name: str
    description: Optional[str]
    tenant_id: UUID


class DomainCreate(DomainBase):
    pass


class Domain(DomainBase):
    domain_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Domain Config Schema
class DomainConfigSchema(BaseModel):
    config_id: UUID
    domain_id: UUID
    tenant_id: UUID
    config_key: str
    config_value: str
    created_at: datetime

    class Config:
        from_attributes = True


# Entity Schemas (replacing Concept, Source, and Methodology)
class EntityBase(BaseModel):
    name: str
    description: Optional[str]
    type: str  # e.g., 'concept', 'source', 'methodology'
    version: int
    metadata: Optional[Dict[str, Any]]


class EntityCreate(EntityBase):
    entity_id: Optional[int]


class Entity(EntityBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# RelationshipEdge Schemas (replacing the old Relationship model)
class RelationshipBase(BaseModel):
    from_entity_id: int
    to_entity_id: int
    name: Optional[str]
    type: Optional[str]
    description: Optional[str]
    metadata: Optional[Dict[str, Any]]


class RelationshipCreate(RelationshipBase):
    id: Optional[int]


class Relationship(RelationshipBase):
    id: int
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


# Domain Data Schema with entities and relationships
class DomainDataSchema(BaseModel):
    domain_id: UUID
    domain_name: str
    description: Optional[str]
    tenant_id: UUID
    version: int
    created_at: datetime
    entities: List[Entity]  # Representing entities (e.g., concepts)
    relationships: List[Relationship]  # Representing relationships

    class Config:
        from_attributes = True


# Schema for saving the domain with new version (updating entities and relationships)
class DomainSaveSchema(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]


# Role Schemas
class RoleBase(BaseModel):
    role_name: str
    description: Optional[str]
    tenant_id: UUID  # Add tenant_id here


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None


class Role(RoleBase):
    role_id: UUID

    class Config:
        from_attributes = True


# UserRole Schemas
class UserRoleBase(BaseModel):
    user_id: UUID
    domain_id: UUID
    role_id: UUID
    tenant_id: UUID  # Add tenant_id here


class UserRoleCreate(BaseModel):
    role_name: str


class UserRole(UserRoleBase):
    role_name: str

    class Config:
        from_attributes = True


class UserRoleResponse(BaseModel):
    user_id: UUID
    domain_id: UUID
    role_name: str
    email: str
    name: str

    class Config:
        from_attributes = True


# Invitation Schemas
class InvitationBase(BaseModel):
    invitee_email: str
    tenant_id: UUID
    domain_id: Optional[UUID] = None
    status: Optional[str] = "pending"
    expires_at: Optional[datetime] = None


class InvitationCreate(InvitationBase):
    pass


class InvitationResponse(InvitationBase):
    invitation_id: UUID
    inviter_user_id: UUID
    created_at: datetime
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
