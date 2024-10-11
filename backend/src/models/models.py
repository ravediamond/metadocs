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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as UUIDType, JSONB
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
    entities = relationship(
        "Entity", back_populates="tenant", cascade="all, delete-orphan"
    )
    relationship_edges = relationship(
        "RelationshipEdge", back_populates="tenant", cascade="all, delete-orphan"
    )


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
    entities = relationship(
        "Entity", back_populates="domain", cascade="all, delete-orphan"
    )
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
    relationship_edges = relationship("RelationshipEdge", back_populates="domain")


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

    # Relationship to entities and relationships (Graph Components)
    entities = relationship("Entity", back_populates="domain_version_rel")
    relationship_edges = relationship(
        "RelationshipEdge", back_populates="domain_version_rel"
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


# Unified Entity Model
class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("domains.domain_id", ondelete="CASCADE"),  # ForeignKey to domains
        nullable=False,
    )
    tenant_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_version = Column(
        Integer,
        ForeignKey("domain_versions.version"),  # ForeignKey to the version column
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(
        String(50), nullable=False
    )  # 'concept', 'source', 'methodology'
    vector = Column(Vector(1536), nullable=True)  # Optional embedding vector
    meta_data = Column(JSONB, nullable=True)  # Additional metadata
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="entities")  # Relationship to Domain
    domain_version_rel = relationship(
        "DomainVersion", back_populates="entities"
    )  # Corrected relationship
    tenant = relationship("Tenant", back_populates="entities")
    outgoing_relationships = relationship(
        "RelationshipEdge",
        foreign_keys="RelationshipEdge.from_entity_id",
        back_populates="from_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "RelationshipEdge",
        foreign_keys="RelationshipEdge.to_entity_id",
        back_populates="to_entity",
        cascade="all, delete-orphan",
    )


# RelationshipEdge Model (Edge in Graph)
class RelationshipEdge(Base):
    __tablename__ = "relationship_edges"

    edge_id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    domain_version = Column(
        Integer,
        ForeignKey(
            "domain_versions.version"
        ),  # Link to the version column of DomainVersion
        nullable=False,
    )
    from_entity_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    to_entity_id = Column(
        UUIDType(as_uuid=True),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type = Column(
        String(50), nullable=False
    )  # e.g., 'related_to', 'part_of'
    vector = Column(
        Vector(1536), nullable=True
    )  # Optional: Vector for the relationship
    meta_data = Column(JSONB, nullable=True)  # Renamed from 'metadata'
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "from_entity_id",
            "to_entity_id",
            "relationship_type",
            "domain_id",
            name="uq_edge_relationship",
        ),
    )

    # Relationships
    domain = relationship("Domain", back_populates="relationship_edges")
    domain_version_rel = relationship(
        "DomainVersion", back_populates="relationship_edges"
    )
    tenant = relationship("Tenant", back_populates="relationship_edges")
    from_entity = relationship(
        "Entity",
        foreign_keys=[from_entity_id],
        back_populates="outgoing_relationships",
    )
    to_entity = relationship(
        "Entity",
        foreign_keys=[to_entity_id],
        back_populates="incoming_relationships",
    )
