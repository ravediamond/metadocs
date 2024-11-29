import uuid
import secrets
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
    files = relationship(
        "File", back_populates="uploader", cascade="all, delete-orphan"
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
    version = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, default=func.now())
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
    filename = Column(String(255), nullable=False)
    filepath = Column(String(1024), nullable=False)
    uploaded_at = Column(TIMESTAMP, default=func.now())
    uploaded_by = Column(
        UUIDType(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    last_processed_at = Column(TIMESTAMP, nullable=True)
    processing_status = Column(String(50), nullable=True)
    processing_error = Column(String(1024), nullable=True)

    markdown_path = Column(String(1024), nullable=True)
    entity_extraction_path = Column(String(1024), nullable=True)
    entity_grouping_path = Column(String(1024), nullable=True)
    ontology_path = Column(String(1024), nullable=True)

    # Add pipeline reference
    pipeline_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("processing_pipeline.pipeline_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    domain = relationship("Domain", back_populates="files")
    uploader = relationship("User", back_populates="files")
    pipeline = relationship("ProcessingPipeline", back_populates="files")


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

    # Current version references
    current_parse_id = Column(UUIDType(as_uuid=True), nullable=True)
    current_extract_id = Column(UUIDType(as_uuid=True), nullable=True)
    current_merge_id = Column(UUIDType(as_uuid=True), nullable=True)
    current_group_id = Column(UUIDType(as_uuid=True), nullable=True)
    current_ontology_id = Column(UUIDType(as_uuid=True), nullable=True)
    current_graph_id = Column(UUIDType(as_uuid=True), nullable=True)

    status = Column(String(50))
    error = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="processing_pipelines")
    domain_version = relationship(
        "DomainVersion", back_populates="processing_pipeline", uselist=False
    )

    # Version relationships
    parse_versions = relationship(
        "ParseVersion",
        primaryjoin="ProcessingPipeline.pipeline_id == ParseVersion.pipeline_id",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    extract_versions = relationship(
        "ExtractVersion",
        primaryjoin="ProcessingPipeline.pipeline_id == ExtractVersion.pipeline_id",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    merge_versions = relationship(
        "MergeVersion",
        primaryjoin="ProcessingPipeline.pipeline_id == MergeVersion.pipeline_id",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    group_versions = relationship(
        "GroupVersion",
        primaryjoin="ProcessingPipeline.pipeline_id == GroupVersion.pipeline_id",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    ontology_versions = relationship(
        "OntologyVersion",
        primaryjoin="ProcessingPipeline.pipeline_id == OntologyVersion.pipeline_id",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    graph_versions = relationship(
        "GraphVersion",
        primaryjoin="ProcessingPipeline.pipeline_id == GraphVersion.pipeline_id",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    files = relationship("File", back_populates="pipeline")

    def add_file(self, file: File) -> bool:
        """Add a file to this pipeline's processing list"""
        if file.domain_id != self.domain_id:
            return False
        file.pipeline_id = self.pipeline_id
        return True

    def remove_file(self, file: File) -> bool:
        """Remove a file from this pipeline's processing list"""
        if file.pipeline_id != self.pipeline_id:
            return False
        file.pipeline_id = None
        return True


class ProcessingVersionMixin:
    """Mixin for version tracking tables with proper declarative attributes"""

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def version_id(cls):
        return Column(UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid)

    @declared_attr
    def pipeline_id(cls):
        return Column(
            UUIDType(as_uuid=True),
            ForeignKey("processing_pipeline.pipeline_id", ondelete="CASCADE"),
            nullable=False,
        )

    version_number = Column(Integer, nullable=False)
    input_path = Column(String(1024))
    output_path = Column(String(1024))
    status = Column(String(50))
    error = Column(String(1024))
    created_at = Column(TIMESTAMP, default=func.now())


class ParseVersion(Base, ProcessingVersionMixin):
    __tablename__ = "parse_versions"

    pipeline = relationship(
        "ProcessingPipeline",
        primaryjoin="ParseVersion.pipeline_id == ProcessingPipeline.pipeline_id",
        back_populates="parse_versions",
    )


class ExtractVersion(Base, ProcessingVersionMixin):
    __tablename__ = "extract_versions"

    pipeline = relationship(
        "ProcessingPipeline",
        primaryjoin="ExtractVersion.pipeline_id == ProcessingPipeline.pipeline_id",
        back_populates="extract_versions",
    )


class MergeVersion(Base, ProcessingVersionMixin):
    __tablename__ = "merge_versions"

    pipeline = relationship(
        "ProcessingPipeline",
        primaryjoin="MergeVersion.pipeline_id == ProcessingPipeline.pipeline_id",
        back_populates="merge_versions",
    )


class GroupVersion(Base, ProcessingVersionMixin):
    __tablename__ = "group_versions"

    pipeline = relationship(
        "ProcessingPipeline",
        primaryjoin="GroupVersion.pipeline_id == ProcessingPipeline.pipeline_id",
        back_populates="group_versions",
    )


class OntologyVersion(Base, ProcessingVersionMixin):
    __tablename__ = "ontology_versions"

    pipeline = relationship(
        "ProcessingPipeline",
        primaryjoin="OntologyVersion.pipeline_id == ProcessingPipeline.pipeline_id",
        back_populates="ontology_versions",
    )


class GraphVersion(Base, ProcessingVersionMixin):
    __tablename__ = "graph_versions"

    pipeline = relationship(
        "ProcessingPipeline",
        primaryjoin="GraphVersion.pipeline_id == ProcessingPipeline.pipeline_id",
        back_populates="graph_versions",
    )
