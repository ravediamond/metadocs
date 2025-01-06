import uuid
import secrets
from typing import List, Optional, Dict
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Text,
    TIMESTAMP,
    Integer,
    func,
    ARRAY,
    select,
    Enum as SQLAlchemyEnum,
    BigInteger,
    ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import relationship, declared_attr, Session
from sqlalchemy.ext.declarative import declarative_base


def generate_api_key():
    return secrets.token_hex(32)


# Define the declarative base
Base = declarative_base()


# Helper function to generate UUIDs
def gen_random_uuid():
    return str(uuid.uuid4())


# Tenant Model
class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    tenant_name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    user_tenants = relationship(
        "UserTenant", back_populates="tenant", cascade="all, delete-orphan"
    )
    domains = relationship(
        "Domain", back_populates="tenant", cascade="all, delete-orphan"
    )
    roles = relationship("Role", back_populates="tenant", cascade="all, delete-orphan")


# UserTenant Association Model
class UserTenant(Base):
    __tablename__ = "user_tenants"

    user_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    user = relationship("User", back_populates="user_tenants")
    tenant = relationship("Tenant", back_populates="user_tenants")
    role = relationship("Role")


# User Model
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    user_tenants = relationship(
        "UserTenant", back_populates="user", cascade="all, delete-orphan"
    )
    user_roles = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    domains = relationship("Domain", back_populates="owner")
    configurations = relationship(
        "UserConfig", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )


# APIKey Model
class APIKey(Base):
    __tablename__ = "api_keys"

    api_key_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    api_key = Column(String(64), unique=True, nullable=False, default=generate_api_key)
    user_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(TIMESTAMP, default=func.now())
    revoked = Column(TIMESTAMP, nullable=True)

    # Relationship with User and Tenant
    user = relationship("User", back_populates="api_keys")
    tenant = relationship("Tenant")


# Domain Model
class Domain(Base):
    __tablename__ = "domains"

    domain_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_name = Column(String(255), nullable=False)
    owner_user_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship to tenant
    tenant = relationship("Tenant", back_populates="domains")
    owner = relationship("User", back_populates="domains")

    # Relationships
    versions = relationship(
        "DomainVersion",
        back_populates="domain",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    configurations = relationship(
        "DomainConfig", back_populates="domain", cascade="all, delete-orphan"
    )
    user_roles = relationship("UserRole", back_populates="domain")
    files = relationship("File", back_populates="domain", cascade="all, delete-orphan")
    processing_pipelines = relationship(
        "ProcessingPipeline", back_populates="domain", cascade="all, delete-orphan"
    )


class DomainVersionStatus(str, Enum):
    DRAFT = "DRAFT"
    TO_BE_VALIDATED = "TO_BE_VALIDATED"
    PUBLISHED = "PUBLISHED"
    PENDING_SUSPENSION = "PENDING_SUSPENSION"
    SUSPENDED = "SUSPENDED"
    PENDING_DELETE = "PENDING_DELETE"
    DELETED = "DELETED"


# DomainVersion Model
class DomainVersion(Base):
    __tablename__ = "domain_versions"

    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, default=func.now())
    status = Column(
        SQLAlchemyEnum(DomainVersionStatus, name="domain_version_status"),
        nullable=False,
        default=DomainVersionStatus.DRAFT,
    )
    pipeline_id = Column(
        UUIDType(as_uuid=True), ForeignKey("processing_pipeline.pipeline_id")
    )

    # Relationships
    domain = relationship("Domain", back_populates="versions")
    tenant = relationship("Tenant")
    processing_pipeline = relationship(
        "ProcessingPipeline",
        back_populates="domain_version",
        single_parent=True,
        uselist=False,  # One-to-one relationship
    )
    file_versions = relationship(
        "DomainVersionFile",
        back_populates="domain_version_ref",
        primaryjoin="and_(DomainVersion.domain_id==DomainVersionFile.domain_id, "
        "DomainVersion.version_number==DomainVersionFile.version_number)",
    )


# DomainConfig Model
class DomainConfig(Base):
    __tablename__ = "domain_config"

    config_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    config_key = Column(String(255), nullable=False)
    config_value = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship with Domain and Tenant
    domain = relationship("Domain", back_populates="configurations")
    tenant = relationship("Tenant")


# UserConfig Model
class UserConfig(Base):
    __tablename__ = "user_config"

    config_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    user_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    config_key = Column(String(255), nullable=False)
    config_value = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship with User and Tenant
    user = relationship("User", back_populates="configurations")
    tenant = relationship("Tenant")


# Role Model
class Role(Base):
    __tablename__ = "roles"

    role_id = Column(UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid)
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    # Relationship to Tenant and UserRole
    tenant = relationship("Tenant", back_populates="roles")
    user_roles = relationship("UserRole", back_populates="role")


# UserRole Association Model
class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    user = relationship("User", back_populates="user_roles")
    domain = relationship("Domain", back_populates="user_roles")
    role = relationship("Role")


# Invitation Model
class Invitation(Base):
    __tablename__ = "invitations"

    invitation_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    inviter_user_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    invitee_email = Column(String(255), nullable=False)
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),
        nullable=True,  # Optional field
    )
    status = Column(String(50), default="pending")
    created_at = Column(TIMESTAMP, default=func.now())
    expires_at = Column(TIMESTAMP, nullable=True)
    accepted_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    inviter = relationship("User", foreign_keys=[inviter_user_id])
    tenant = relationship("Tenant")
    domain = relationship("Domain", foreign_keys=[domain_id])


class File(Base):
    __tablename__ = "files"

    file_id = Column(UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid)
    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="files")
    tenant = relationship("Tenant")
    versions = relationship(
        "FileVersion", back_populates="file", cascade="all, delete-orphan"
    )


class FileVersion(Base):
    __tablename__ = "file_versions"

    file_version_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    file_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("files.file_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    filepath = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    uploaded_at = Column(TIMESTAMP, default=func.now())
    uploaded_by = Column(
        UUIDType(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    file = relationship("File", back_populates="versions")
    uploader = relationship("User")
    domain_versions = relationship("DomainVersionFile", back_populates="file_version")


class DomainVersionFile(Base):
    __tablename__ = "domain_version_files"

    domain_id = Column(UUIDType(as_uuid=True), primary_key=True)
    version_number = Column(Integer, primary_key=True)
    file_version_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("file_versions.file_version_id", ondelete="CASCADE"),
        primary_key=True,
    )
    error = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    domain_version_ref = relationship(
        "DomainVersion",
        foreign_keys=[domain_id, version_number],
        back_populates="file_versions",
    )
    file_version = relationship("FileVersion", back_populates="domain_versions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "version_number"],
            ["domain_versions.domain_id", "domain_versions.version_number"],
            ondelete="CASCADE",
        ),
    )


class PipelineStage(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PARSE = "PARSE"
    EXTRACT = "EXTRACT"
    GRAPH = "GRAPH"
    COMPLETED = "COMPLETED"


class PipelineStatus(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingPipeline(Base):
    __tablename__ = "processing_pipeline"
    pipeline_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),
        nullable=False,
    )
    stage = Column(
        SQLAlchemyEnum(PipelineStage, name="pipeline_stage"),
        nullable=False,
        default=PipelineStage.NOT_STARTED,
    )
    status = Column(
        SQLAlchemyEnum(PipelineStatus, name="pipeline_status"),
        nullable=False,
        default=PipelineStatus.UNINITIALIZED,
    )
    error = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="processing_pipelines")
    domain_version = relationship(
        "DomainVersion", back_populates="processing_pipeline", uselist=False
    )

    # Version relationships
    parse_versions = relationship(
        "ParseVersion", back_populates="pipeline", cascade="all, delete-orphan"
    )
    extract_versions = relationship(
        "ExtractVersion", back_populates="pipeline", cascade="all, delete-orphan"
    )
    graph_versions = relationship(
        "GraphVersion", back_populates="pipeline", cascade="all, delete-orphan"
    )

    def get_stage_status(self, stage: PipelineStage) -> PipelineStatus:
        """Get the status of a specific stage based on its versions"""
        if stage == PipelineStage.NOT_STARTED:
            return PipelineStatus.UNINITIALIZED

        version_map = {
            PipelineStage.PARSE: self.parse_versions,
            PipelineStage.EXTRACT: self.extract_versions,
            PipelineStage.GRAPH: self.graph_versions,
        }

        versions = version_map.get(stage, [])
        if not versions:
            return PipelineStatus.UNINITIALIZED

        if any(v.status == "failed" for v in versions):
            return PipelineStatus.FAILED

        if all(v.status == "completed" for v in versions):
            return PipelineStatus.COMPLETED

        return PipelineStatus.RUNNING

    def can_start_stage(self, stage: PipelineStage) -> bool:
        """Check if a stage can be started based on dependencies"""
        if stage == PipelineStage.PARSE:
            return True

        elif stage == PipelineStage.EXTRACT:
            return (
                self.get_stage_status(PipelineStage.PARSE) == PipelineStatus.COMPLETED
            )

        elif stage == PipelineStage.GRAPH:
            return (
                self.get_stage_status(PipelineStage.EXTRACT) == PipelineStatus.COMPLETED
            )

        return False

    def get_latest_version_by_stage(self, stage: PipelineStage) -> Optional[UUIDType]:
        """Get the latest version ID for a specific stage"""
        version_map = {
            PipelineStage.PARSE: self.parse_versions,
            PipelineStage.EXTRACT: self.extract_versions,
            PipelineStage.GRAPH: self.graph_versions,
        }

        versions = version_map.get(stage, [])
        latest = next(
            iter(sorted(versions, key=lambda x: x.version_number, reverse=True)), None
        )
        return latest.version_id if latest else None

    def get_stage_versions(self, stage: PipelineStage) -> List[Dict]:
        """Get all versions and their statuses for a stage"""
        version_map = {
            PipelineStage.PARSE: self.parse_versions,
            PipelineStage.EXTRACT: self.extract_versions,
            PipelineStage.GRAPH: self.graph_versions,
        }

        versions = version_map.get(stage, [])
        return [
            {
                "version_id": v.version_id,
                "status": v.status,
                "number": v.version_number,
                "created_at": v.created_at,
                "error": v.errors if hasattr(v, "errors") else v.error,
            }
            for v in sorted(versions, key=lambda x: x.version_number)
        ]

    def update_pipeline_status(self) -> None:
        """Update overall pipeline status based on current stage"""
        current_stage_status = self.get_stage_status(self.stage)
        self.status = current_stage_status


class ParseVersion(Base):
    __tablename__ = "parse_versions"

    version_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    pipeline_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("processing_pipeline.pipeline_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    system_prompt = Column(Text, nullable=False)
    readability_prompt = Column(Text, nullable=False)
    convert_prompt = Column(Text, nullable=False)
    custom_instructions = Column(ARRAY(Text))
    input_file_version_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("file_versions.file_version_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(50), nullable=False)
    output_dir = Column(String(1024), nullable=False)
    output_path = Column(String(1024), nullable=False)
    errors = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship
    pipeline = relationship("ProcessingPipeline", back_populates="parse_versions")
    input_file_version = relationship("FileVersion")
    extract_versions = relationship("ExtractVersion", back_populates="parse_version")


class ExtractVersion(Base):
    __tablename__ = "extract_versions"

    version_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    pipeline_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("processing_pipeline.pipeline_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    system_prompt = Column(Text, nullable=False)
    initial_entity_extraction_prompt = Column(Text, nullable=False)
    iterative_extract_entities_prompt = Column(Text, nullable=False)
    entity_details_prompt = Column(Text, nullable=False)
    custom_instructions = Column(ARRAY(Text))
    input_parse_version_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("parse_versions.version_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(50), nullable=False)
    output_dir = Column(String(1024), nullable=False)
    output_path = Column(String(1024), nullable=False)
    errors = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship
    pipeline = relationship("ProcessingPipeline", back_populates="extract_versions")
    parse_version = relationship("ParseVersion", back_populates="extract_versions")


class GraphVersion(Base):
    __tablename__ = "graph_versions"
    version_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    pipeline_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("processing_pipeline.pipeline_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    input_extract_version_ids = Column(ARRAY(UUIDType(as_uuid=True)), nullable=False)
    status = Column(String(50))
    error = Column(String(1024))
    output_dir = Column(String(1024), nullable=False)
    output_path = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship
    pipeline = relationship("ProcessingPipeline", back_populates="graph_versions")
