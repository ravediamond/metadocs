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
    revoked: Optional[datetime] = None


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
    description: Optional[str] = None
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
    description: Optional[str] = None
    type: str  # e.g., 'concept', 'source', 'methodology'
    version: Optional[int] = 1
    metadata: Optional[Dict[str, Any]] = None


class EntityCreate(EntityBase):
    id: Optional[str] = None


class Entity(EntityBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# RelationshipEdge Schemas (replacing the old Relationship model)
class RelationshipBase(BaseModel):
    from_entity_id: str
    to_entity_id: str
    name: str
    type: str
    description: Optional[str] = None
    version: Optional[int] = 1
    metadata: Optional[Dict[str, Any]] = None


class RelationshipCreate(RelationshipBase):
    id: Optional[str] = None


class Relationship(RelationshipBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Domain Data Schema with entities and relationships
class DomainDataSchema(BaseModel):
    domain_id: UUID
    domain_name: str
    description: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    entities: Dict[str, Any]
    groups: List[Dict[str, Any]]
    ontology: Dict[str, Any]
    processing_id: Optional[UUID]
    last_processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DomainVersionSchema(BaseModel):
    domain_id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    entity_grouping_path: str
    ontology_path: str
    file_id: UUID

    class Config:
        from_attributes = True


# Role Schemas
class RoleBase(BaseModel):
    role_name: str
    description: Optional[str] = None
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


class FileBase(BaseModel):
    filename: str


class FileCreate(FileBase):
    pass


class FileResponse(BaseModel):
    file_id: UUID
    domain_id: UUID
    filename: str
    filepath: str
    uploaded_at: datetime
    uploaded_by: Optional[UUID] = None
    last_processed_at: Optional[datetime] = None
    processing_status: Optional[str] = None
    processing_error: Optional[str] = None
    markdown_path: Optional[str] = None
    entity_extraction_path: Optional[str] = None
    ontology_path: Optional[str] = None

    class Config:
        from_attributes = True


class FileStatus(BaseModel):
    file_id: str
    filename: str
    status: (
        str  # "queued", "processing_pdf", "processing_entities", "completed", "failed"
    )
    error: Optional[str] = None
    markdown_path: Optional[str] = None
    entity_extraction_path: Optional[str] = None
    ontology_path: Optional[str] = None
    last_processed_at: Optional[datetime] = None
    processing_details: Dict[str, Any]

    class Config:
        from_attributes = True


class ProcessingStatus(BaseModel):
    message: str
    total_files: int
    files_completed: Optional[int] = 0
    files_failed: Optional[int] = 0
    files_processing: Optional[int] = 0
    processing_started: bool
    file_statuses: Optional[List[FileStatus]] = None

    class Config:
        from_attributes = True


class ProcessPipelineSchema(BaseModel):
    processing_id: UUID
    domain_id: UUID
    status: str
    error: Optional[str]
    merged_entities_path: Optional[str]
    entity_grouping_path: Optional[str]
    ontology_path: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    file_ids: List[UUID]

    class Config:
        from_attributes = True


class ProcessingVersionBase(BaseModel):
    version_id: UUID
    pipeline_id: UUID
    version_number: int
    input_path: Optional[str]
    output_path: Optional[str]
    status: str
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ParseVersion(ProcessingVersionBase):
    """Version info for PDF parsing stage"""

    pass


class ExtractVersion(ProcessingVersionBase):
    """Version info for entity extraction stage"""

    pass


class MergeVersion(ProcessingVersionBase):
    """Version info for entity merging stage"""

    pass


class GroupVersion(ProcessingVersionBase):
    """Version info for entity grouping stage"""

    pass


class OntologyVersion(ProcessingVersionBase):
    """Version info for ontology generation stage"""

    pass


class GraphVersion(ProcessingVersionBase):
    """Version info for graph generation stage"""

    pass


class ProcessingPipeline(BaseModel):
    pipeline_id: UUID
    domain_id: UUID
    current_parse_id: Optional[UUID]
    current_extract_id: Optional[UUID]
    current_merge_id: Optional[UUID]
    current_group_id: Optional[UUID]
    current_ontology_id: Optional[UUID]
    current_graph_id: Optional[UUID]
    status: str
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DomainBasicResponse(BaseModel):
    domain_id: UUID
    domain_name: str
    description: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    owner_user_id: UUID
    latest_pipeline: Optional[ProcessPipelineSchema] = None
    file_count: int
    version_count: int
    latest_version: Optional[int] = None

    class Config:
        from_attributes = True
