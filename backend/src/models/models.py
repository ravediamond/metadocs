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


# User Model
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship to domains
    domains = relationship("Domain", back_populates="owner")

    # Add the relationship to UserConfig
    configurations = relationship(
        "UserConfig", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationship to API keys
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationship to UserRole
    user_roles = relationship("UserRole", back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"

    api_key_id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key = Column(String(64), unique=True, nullable=False, default=generate_api_key)
    user_id = Column(
        UUIDType(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    created_at = Column(TIMESTAMP, default=func.now())
    revoked = Column(TIMESTAMP, nullable=True)

    # Relationship with User
    user = relationship("User", back_populates="api_keys")


# Domain Model
class Domain(Base):
    __tablename__ = "domains"

    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    domain_name = Column(String(255), nullable=False)
    owner_user_id = Column(
        UUIDType(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (PrimaryKeyConstraint("domain_id", "version"),)

    # Relationships to other models
    concepts = relationship(
        "Concept",
        back_populates="domain",
        cascade="all, delete-orphan",
        primaryjoin="and_(Domain.domain_id==Concept.domain_id, Domain.version==Concept.domain_version)",
    )
    sources = relationship(
        "Source",
        back_populates="domain",
        cascade="all, delete-orphan",
        primaryjoin="and_(Domain.domain_id==Source.domain_id, Domain.version==Source.domain_version)",
    )
    methodologies = relationship(
        "Methodology",
        back_populates="domain",
        cascade="all, delete-orphan",
        primaryjoin="and_(Domain.domain_id==Methodology.domain_id, Domain.version==Methodology.domain_version)",
    )
    relationships = relationship(
        "Relationship",
        back_populates="domain",
        cascade="all, delete-orphan",
        primaryjoin="and_(Domain.domain_id==Relationship.domain_id, Domain.version==Relationship.domain_version)",
    )

    # Add the relationship to DomainConfig
    configurations = relationship(
        "DomainConfig", back_populates="domain", cascade="all, delete-orphan"
    )

    # Relationship to user
    owner = relationship("User", back_populates="domains")

    # Relationship to UserRole
    user_roles = relationship("UserRole", back_populates="domain")


# Concept Model
class Concept(Base):
    __tablename__ = "concepts"

    concept_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
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
        PrimaryKeyConstraint("concept_id", "domain_version"),
        ForeignKeyConstraint(
            ["domain_id", "domain_version"], ["domains.domain_id", "domains.version"]
        ),
    )

    # Relationship with Domain
    domain = relationship(
        "Domain",
        back_populates="concepts",
        primaryjoin="and_(Concept.domain_id==Domain.domain_id, Concept.domain_version==Domain.version)",
    )


# Source Model
class Source(Base):
    __tablename__ = "sources"

    source_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50))  # 'table', 'api', etc.
    location = Column(Text, nullable=False)  # URI, table name, or connection string
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("source_id", "domain_version"),
        ForeignKeyConstraint(
            ["domain_id", "domain_version"], ["domains.domain_id", "domains.version"]
        ),
    )

    # Relationship with Domain
    domain = relationship(
        "Domain",
        back_populates="sources",
        primaryjoin="and_(Source.domain_id==Domain.domain_id, Source.domain_version==Domain.version)",
    )


# Methodology Model
class Methodology(Base):
    __tablename__ = "methodologies"

    methodology_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    steps = Column(
        Text, nullable=False
    )  # Detailed steps on how to join sources or get data
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("methodology_id", "domain_version"),
        ForeignKeyConstraint(
            ["domain_id", "domain_version"], ["domains.domain_id", "domains.version"]
        ),
    )

    # Relationship with Domain
    domain = relationship(
        "Domain",
        back_populates="methodologies",
        primaryjoin="and_(Methodology.domain_id==Domain.domain_id, Methodology.domain_version==Domain.version)",
    )


# Relationship Model
class Relationship(Base):
    __tablename__ = "relationships"

    relationship_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_id = Column(UUIDType(as_uuid=True), nullable=False)
    domain_version = Column(Integer, nullable=False)
    entity_id_1 = Column(
        UUIDType(as_uuid=True), nullable=False
    )  # Can point to concept, methodology, or source
    entity_type_1 = Column(
        String(50), nullable=False
    )  # 'concept', 'methodology', 'source'
    entity_id_2 = Column(
        UUIDType(as_uuid=True), nullable=False
    )  # Can point to concept, methodology, or source
    entity_type_2 = Column(
        String(50), nullable=False
    )  # 'concept', 'methodology', 'source'
    relationship_type = Column(String(50))  # 'related_to', 'part_of', 'depends_on'
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("relationship_id", "domain_version"),
        ForeignKeyConstraint(
            ["domain_id", "domain_version"], ["domains.domain_id", "domains.version"]
        ),
    )

    # Relationship with Domain
    domain = relationship(
        "Domain",
        back_populates="relationships",
        primaryjoin="and_(Relationship.domain_id==Domain.domain_id, Relationship.domain_version==Domain.version)",
    )


# DomainConfig Model
class DomainConfig(Base):
    __tablename__ = "domain_config"

    config_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True), ForeignKey("domains.domain_id"), nullable=False
    )
    config_key = Column(String(255), nullable=False)
    config_value = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship with Domain
    domain = relationship("Domain", back_populates="configurations")


# UserConfig Model
class UserConfig(Base):
    __tablename__ = "user_config"

    config_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    user_id = Column(
        UUIDType(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    config_key = Column(String(255), nullable=False)
    config_value = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship with User
    user = relationship("User", back_populates="configurations")


# Role Model
class Role(Base):
    __tablename__ = "roles"

    role_id = Column(UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    # Relationship to UserRole
    user_roles = relationship("UserRole", back_populates="role")


# UserRole Association Model
class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(
        UUIDType(as_uuid=True), ForeignKey("users.user_id"), primary_key=True
    )
    domain_id = Column(
        UUIDType(as_uuid=True), ForeignKey("domains.domain_id"), primary_key=True
    )
    role_id = Column(
        UUIDType(as_uuid=True), ForeignKey("roles.role_id"), primary_key=True
    )

    # Relationships
    user = relationship("User", back_populates="user_roles")
    domain = relationship("Domain", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
