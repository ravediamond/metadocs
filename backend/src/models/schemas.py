from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
from .models import DomainVersionStatus, PipelineStage, PipelineStatus


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


class DomainUpdate(BaseModel):
    domain_name: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


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
    domain_id: UUID
    tenant_id: UUID
    filename: str


class FileVersion(BaseModel):
    file_version_id: UUID
    file_id: UUID
    version_number: int
    file_size: int
    filepath: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileVersionBase(BaseModel):
    filename: str
    file_type: str
    file_size: int
    filepath: str


class FileVersionCreate(FileVersionBase):
    file_id: UUID
    version_number: int


class FileVersion(FileVersionBase):
    file_version_id: UUID
    file_id: UUID
    version_number: int
    uploaded_at: datetime
    uploaded_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class File(FileBase):
    file_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class FileCreate(FileBase):
    pass


class FileResponse(FileBase):
    file_id: UUID
    uploaded_at: datetime
    uploaded_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class FileVersionResponse(FileVersion):
    class Config:
        from_attributes = True


class FileWithVersionsResponse(File):
    versions: List[FileVersionResponse]

    class Config:
        from_attributes = True


class DomainVersionFile(BaseModel):
    domain_id: UUID
    version_number: int
    file_version_id: UUID
    error: Optional[str] = None
    created_at: datetime
    filename: Optional[str] = None

    class Config:
        from_attributes = True


class DomainVersionSchema(BaseModel):
    domain_id: UUID
    tenant_id: UUID
    version_number: int
    created_at: datetime
    status: DomainVersionStatus
    pipeline_id: Optional[UUID]
    file_versions: List[DomainVersionFile]

    class Config:
        from_attributes = True


class ProcessingStatus(BaseModel):
    """Processing status that references current ParseVersion status"""

    message: str
    total_files: int
    files_completed: Optional[int] = 0
    files_failed: Optional[int] = 0
    files_processing: Optional[int] = 0
    processing_started: bool
    parse_status: Optional[str] = None

    class Config:
        from_attributes = True


class ProcessingPipeline(BaseModel):
    pipeline_id: UUID
    domain_id: UUID
    stage: PipelineStage
    status: PipelineStatus
    error: Optional[str]
    created_at: datetime
    # Latest version IDs
    latest_parse_version_id: Optional[UUID] = None
    latest_extract_version_id: Optional[UUID] = None
    latest_merge_version_id: Optional[UUID] = None
    latest_group_version_id: Optional[UUID] = None
    latest_ontology_version_id: Optional[UUID] = None
    latest_graph_version_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class ProcessingVersionBase(BaseModel):
    version_id: UUID
    pipeline_id: UUID
    version_number: int
    created_at: datetime

    class Config:
        from_attributes = True


class ParseVersion(ProcessingVersionBase):
    """Version info for PDF parsing stage"""

    system_prompt: str
    readability_prompt: str
    convert_prompt: str
    input_file_version_id: UUID
    custom_instructions: List[str]
    status: str
    output_dir: str
    output_path: str
    errors: Optional[str]

    class Config:
        from_attributes = True


class ExtractVersion(ProcessingVersionBase):
    """Version info for entity extraction stage"""

    system_prompt: str
    initial_entity_extraction_prompt: str
    iterative_extract_entities_prompt: str
    entity_details_prompt: str
    input_extraction_version_id: UUID
    custom_instructions: List[str]
    status: str
    output_dir: str
    output_path: str
    errors: Optional[str]

    class Config:
        from_attributes = True


class MergeVersion(ProcessingVersionBase):
    """Version info for entity merging stage"""

    system_prompt: str
    entity_details_prompt: str
    entity_merge_prompt: str
    input_extract_version_ids: List[UUID]
    custom_instructions: List[str]
    output_dir: str
    output_path: Optional[str]
    status: Optional[str]
    error: Optional[str]

    class Config:
        from_attributes = True


class GroupVersion(ProcessingVersionBase):
    """Version info for entity grouping stage"""

    system_prompt: str
    entity_group_prompt: str
    input_merge_version_id: UUID
    custom_instructions: List[str]
    output_dir: str
    output_path: Optional[str]
    status: Optional[str]
    error: Optional[str]

    class Config:
        from_attributes = True


class OntologyVersion(ProcessingVersionBase):
    """Version info for ontology generation stage"""

    system_prompt: str
    ontology_prompt: str
    input_group_version_id: UUID
    input_merge_version_id: UUID
    custom_instructions: List[str]
    output_dir: str
    output_path: Optional[str]
    status: Optional[str]
    error: Optional[str]

    class Config:
        from_attributes = True


class GraphVersion(ProcessingVersionBase):
    """Version info for graph generation stage"""

    input_group_version_id: UUID
    input_merge_version_id: UUID
    input_ontology_version_id: UUID
    output_dir: str
    output_path: Optional[str]
    status: Optional[str]
    error: Optional[str]

    class Config:
        from_attributes = True


class DomainBasicResponse(BaseModel):
    domain_id: UUID
    domain_name: str
    description: Optional[str] = None
    tenant_id: UUID
    created_at: datetime
    owner_user_id: UUID
    latest_pipeline: Optional[ProcessingPipeline] = None
    file_count: int
    version_count: int
    latest_version: Optional[int] = None

    class Config:
        from_attributes = True


class MergeRequest(BaseModel):
    extract_version_ids: List[UUID]


class OntologyRequest(BaseModel):
    merge_version_id: UUID
    group_version_id: UUID


class FileVersionsRequest(BaseModel):
    file_version_ids: List[UUID]


class BasePrompts(BaseModel):
    system_prompt: str
    custom_instructions: List[str]


class ParsePrompts(BasePrompts):
    readability_prompt: str
    convert_prompt: str


class ExtractPrompts(BasePrompts):
    initial_entity_extraction_prompt: str
    iterative_extract_entities_prompt: str
    entity_details_prompt: str


class MergePrompts(BasePrompts):
    entity_details_prompt: str
    entity_merge_prompt: str


class GroupPrompts(BasePrompts):
    entity_group_prompt: str


class OntologyPrompts(BasePrompts):
    ontology_prompt: str


class StageStartResponse(BaseModel):
    message: str
    pipeline_id: UUID
    version_id: UUID
    input_version_ids: List[UUID]


class StageDependencyInfo(BaseModel):
    stage: PipelineStage
    completed: bool


class StageDependenciesResponse(BaseModel):
    stage: PipelineStage
    dependencies: List[StageDependencyInfo]
    can_start: bool

    class Config:
        from_attributes = True


class StartedVersionInfo(BaseModel):
    message: str
    pipeline_id: UUID
    version_id: UUID
    input_version_ids: List[UUID]


class StageVersionInfo(BaseModel):
    version_id: UUID
    status: str
    number: int
    created_at: datetime
    error: Optional[str] = None

    class Config:
        from_attributes = True


class StageStatusResponse(BaseModel):
    stage: PipelineStage
    status: PipelineStatus
    can_start: bool
    versions: List[StageVersionInfo]
    latest_version_id: Optional[UUID]

    class Config:
        from_attributes = True


class StageBatchResponse(BaseModel):
    message: str
    started_versions: List[StartedVersionInfo]


class PipelineActionResponse(BaseModel):
    """Response model for pipeline actions (start, stop, restart)"""

    message: str
    pipeline_id: UUID

    class Config:
        from_attributes = True


class PipelineStartRequest(BaseModel):
    """Optional configuration for pipeline start"""

    skip_stages: Optional[List[PipelineStage]] = None
    custom_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PipelineErrorResponse(BaseModel):
    """Error response for pipeline operations"""

    detail: str
    error_code: Optional[str] = None
    stage: Optional[PipelineStage] = None
    version_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    content: str = Field(description="The message content from the user")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "How are entities X and Y related in the knowledge graph?"
            }
        }


class ChatVersionState(BaseModel):
    """Schema for providing version information"""

    parse_versions: Dict[UUID, UUID]  # file_version_id -> parse_version_id
    extract_versions: Dict[UUID, UUID]  # parse_version_id -> extract_version_id
    merge_version_id: Optional[UUID]
    group_version_id: Optional[UUID]
    ontology_version_id: Optional[UUID]


class ChatMessage(BaseModel):
    """Schema for chat messages"""

    content: str


class ChatRequest(BaseModel):
    """Schema for chat requests"""

    message: ChatMessage
    versions: ChatVersionState


class ChatResponse(BaseModel):
    """Schema for chat responses"""

    message_id: UUID = Field(default_factory=uuid4)
    message_type: str = Field(
        description="Type of message: 'question' or 'modification'"
    )
    intent: str = Field(description="Specific intent of the message")
    response: str = Field(description="Assistant's response")
    todo_list: Optional[List[Dict]] = Field(
        default=None, description="Updated todo list if changes were approved"
    )


class MessageType(str, Enum):
    """Enum for different types of messages"""

    TEXT = "text"
    ERROR = "error"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ACTION = "action"


class IntentType(str, Enum):
    """Enum for different types of intents"""

    CREATE_VERSION = "create_version"
    MODIFY_PROMPT = "modify_prompt"
    ANALYZE_RESULTS = "analyze_results"
    START_PROCESSING = "start_processing"
    GET_STATUS = "get_status"
    HELP = "help"
    UNKNOWN = "unknown"
    ERROR = "error"


class MessageContent(BaseModel):
    """Schema for message content"""

    content: str = Field(..., description="The actual message content")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata for the message"
    )


class VersionInfo(BaseModel):
    """Schema for version information"""

    parse_versions: Dict[str, str] = Field(
        default_factory=dict, description="Map of file IDs to parse version IDs"
    )
    extract_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of parse version IDs to extract version IDs",
    )
    merge_version_id: Optional[str] = Field(
        default=None, description="ID of the merge version"
    )
    group_version_id: Optional[str] = Field(
        default=None, description="ID of the group version"
    )
    ontology_version_id: Optional[str] = Field(
        default=None, description="ID of the ontology version"
    )


class ChatRequest(BaseModel):
    """Schema for chat requests"""

    message: MessageContent
    versions: VersionInfo = Field(default_factory=VersionInfo)


class ChatResponse(BaseModel):
    """Schema for chat responses"""

    message_type: MessageType
    intent: IntentType
    response: str
    suggestions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    todo_list: List[str] = Field(default_factory=list)


class GraphState(BaseModel):
    """Schema for graph processing state"""

    message: str
    tenant_id: UUID
    domain_id: UUID
    domain_version: int
    parse_versions: Dict[str, str] = Field(default_factory=dict)
    extract_versions: Dict[str, str] = Field(default_factory=dict)
    merge_version_id: Optional[str] = None
    group_version_id: Optional[str] = None
    ontology_version_id: Optional[str] = None
    message_type: Optional[MessageType] = None
    intent: Optional[IntentType] = None
    loaded_data: Dict[str, Any] = Field(default_factory=dict)
    proposed_changes: List[Dict[str, Any]] = Field(default_factory=list)
    todo_list: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True  # To allow SQLAlchemy Session


class IntentDetectionResult(BaseModel):
    """Schema for intent detection results"""

    success: bool
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class ResponseGenerationResult(BaseModel):
    """Schema for response generation results"""

    success: bool
    message_type: MessageType
    response: str
    suggestions: List[str] = Field(default_factory=list)
    todo_list: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class BaseGraphState(BaseModel):
    """Base state model for graph processing"""

    # Core message and identification details
    message: str
    tenant_id: UUID
    domain_id: UUID
    domain_version: int

    # Processing version tracking
    parse_versions: Dict[str, str] = Field(default_factory=dict)
    extract_versions: Dict[str, str] = Field(default_factory=dict)
    merge_version_id: Optional[str] = None
    group_version_id: Optional[str] = None
    ontology_version_id: Optional[str] = None

    # Message metadata
    message_type: Optional[MessageType] = None
    intent: Optional[IntentType] = None

    # Additional processing metadata
    loaded_data: Dict[str, Any] = Field(default_factory=dict)
    proposed_changes: List[Dict[str, Any]] = Field(default_factory=list)
    todo_list: List[str] = Field(default_factory=list)

    # Database connection (if needed)
    db: Optional[Any] = None

    class Config:
        """Pydantic configuration"""

        arbitrary_types_allowed = True
        from_attributes = True
