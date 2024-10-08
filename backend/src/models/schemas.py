from pydantic import BaseModel, EmailStr
from typing import List, Optional
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
    tenant_id: UUID  # Add tenant_id here
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
    tenant_id: UUID  # Add tenant_id here
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


# Concept Schemas
class ConceptBase(BaseModel):
    name: str
    description: Optional[str]
    type: Optional[str]
    tenant_id: UUID  # Add tenant_id here


class ConceptCreate(ConceptBase):
    concept_id: Optional[UUID]


class Concept(ConceptBase):
    concept_id: UUID
    domain_id: UUID
    domain_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Source Schemas
class SourceBase(BaseModel):
    name: str
    description: Optional[str]
    source_type: Optional[str]
    location: Optional[str]
    tenant_id: UUID  # Add tenant_id here


class SourceCreate(SourceBase):
    source_id: Optional[UUID]


class Source(SourceBase):
    source_id: UUID
    domain_id: UUID
    domain_version: int
    created_at: datetime

    class Config:
        from_attributes = True


# Methodology Schemas
class MethodologyBase(BaseModel):
    name: str
    description: Optional[str]
    steps: Optional[str]
    tenant_id: UUID  # Add tenant_id here


class MethodologyCreate(MethodologyBase):
    methodology_id: Optional[UUID]


class Methodology(MethodologyBase):
    methodology_id: UUID
    domain_id: UUID
    domain_version: int
    created_at: datetime

    class Config:
        from_attributes = True


# Relationship Schemas
class RelationshipBase(BaseModel):
    entity_id_1: UUID
    entity_type_1: str
    entity_id_2: UUID
    entity_type_2: str
    relationship_type: Optional[str]
    tenant_id: UUID  # Add tenant_id here


class RelationshipCreate(RelationshipBase):
    relationship_id: Optional[UUID]


class Relationship(RelationshipBase):
    relationship_id: UUID
    domain_id: UUID
    domain_version: int
    created_at: datetime

    class Config:
        from_attributes = True


# Domain Config Schema
class DomainConfig(BaseModel):
    config_id: UUID
    domain_id: UUID
    tenant_id: UUID  # Add tenant_id here
    config_key: str
    config_value: str
    created_at: datetime

    class Config:
        from_attributes = True


# Updated Domain Data Schema to include domain-level info
class DomainDataSchema(BaseModel):
    domain_id: UUID
    domain_name: str
    description: Optional[str]
    tenant_id: UUID
    version: int
    created_at: datetime
    concepts: List[Concept]
    sources: List[Source]
    methodologies: List[Methodology]
    relationships: List[Relationship]


class DomainSaveSchema(BaseModel):
    concepts: List[Concept]
    sources: List[Source]
    methodologies: List[Methodology]
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
