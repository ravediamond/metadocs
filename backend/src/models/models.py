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
    PrimaryKeyConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from .custom_types import Vector  # Import the custom Vector type


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
    owner = relationship("User", back_populates="domains")
    user_roles = relationship("UserRole", back_populates="domain")


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

    # Relationships
    domain = relationship("Domain", back_populates="versions")
    tenant = relationship("Tenant")

    concepts = relationship(
        "Concept",
        back_populates="domain_version_rel",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(DomainVersion.domain_id==Concept.domain_id, "
            "DomainVersion.version==Concept.domain_version)"
        ),
    )
    sources = relationship(
        "Source",
        back_populates="domain_version_rel",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(DomainVersion.domain_id==Source.domain_id, "
            "DomainVersion.version==Source.domain_version)"
        ),
    )
    methodologies = relationship(
        "Methodology",
        back_populates="domain_version_rel",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(DomainVersion.domain_id==Methodology.domain_id, "
            "DomainVersion.version==Methodology.domain_version)"
        ),
    )
    relationships = relationship(
        "Relationship",
        back_populates="domain_version_rel",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(DomainVersion.domain_id==Relationship.domain_id, "
            "DomainVersion.version==Relationship.domain_version)"
        ),
    )


# Concept Model
class Concept(Base):
    __tablename__ = "concepts"

    # Columns
    concept_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50))
    embedding = Column(Vector(1536))
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(
        TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "domain_version"],
            ["domain_versions.domain_id", "domain_versions.version"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "concept_id", "domain_id", "domain_version", name="uq_concept_version"
        ),
    )

    # Relationship with DomainVersion
    domain_version_rel = relationship(
        "DomainVersion",
        back_populates="concepts",
        primaryjoin=(
            "and_(Concept.domain_id==DomainVersion.domain_id, "
            "Concept.domain_version==DomainVersion.version)"
        ),
    )

    # Relationship with Tenant
    tenant = relationship("Tenant")


# Source Model
class Source(Base):
    __tablename__ = "sources"

    source_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50))  # 'table', 'api', etc.
    location = Column(Text, nullable=False)  # URI, table name, or connection string
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "domain_version"],
            ["domain_versions.domain_id", "domain_versions.version"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "source_id", "domain_id", "domain_version", name="uq_source_version"
        ),
    )

    # Relationship with DomainVersion
    domain_version_rel = relationship(
        "DomainVersion",
        back_populates="sources",
        primaryjoin=(
            "and_(Source.domain_id==DomainVersion.domain_id, "
            "Source.domain_version==DomainVersion.version)"
        ),
    )

    # Relationship with Tenant
    tenant = relationship("Tenant")


# Methodology Model
class Methodology(Base):
    __tablename__ = "methodologies"

    methodology_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    steps = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "domain_version"],
            ["domain_versions.domain_id", "domain_versions.version"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "methodology_id",
            "domain_id",
            "domain_version",
            name="uq_methodology_version",
        ),
    )

    # Relationship with DomainVersion
    domain_version_rel = relationship(
        "DomainVersion",
        back_populates="methodologies",
        primaryjoin=(
            "and_(Methodology.domain_id==DomainVersion.domain_id, "
            "Methodology.domain_version==DomainVersion.version)"
        ),
    )

    # Relationship with Tenant
    tenant = relationship("Tenant")


# Relationship Model
class Relationship(Base):
    __tablename__ = "relationships"

    relationship_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_version = Column(Integer, nullable=False)
    entity_id_1 = Column(UUIDType(as_uuid=True), nullable=False)
    entity_type_1 = Column(
        String(50), nullable=False
    )  # 'concept', 'methodology', 'source'
    entity_id_2 = Column(UUIDType(as_uuid=True), nullable=False)
    entity_type_2 = Column(
        String(50), nullable=False
    )  # 'concept', 'methodology', 'source'
    relationship_type = Column(String(50))  # 'related_to', 'part_of', 'depends_on'
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["domain_id", "domain_version"],
            ["domain_versions.domain_id", "domain_versions.version"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "relationship_id",
            "domain_id",
            "domain_version",
            name="uq_relationship_version",
        ),
    )

    # Relationship with DomainVersion
    domain_version_rel = relationship(
        "DomainVersion",
        back_populates="relationships",
        primaryjoin=(
            "and_(Relationship.domain_id==DomainVersion.domain_id, "
            "Relationship.domain_version==DomainVersion.version)"
        ),
    )

    # Relationship with Tenant
    tenant = relationship("Tenant")


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
