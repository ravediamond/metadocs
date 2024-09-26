from sqlalchemy import Column, String, ForeignKey, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .custom_types import Vector  # Import the custom Vector type
import uuid

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


# Domain Model
class Domain(Base):
    __tablename__ = "domains"

    domain_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_name = Column(String(255), nullable=False)
    owner_user_id = Column(
        UUIDType(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationships to other models
    concepts = relationship(
        "Concept", back_populates="domain", cascade="all, delete-orphan"
    )
    sources = relationship(
        "Source", back_populates="domain", cascade="all, delete-orphan"
    )
    methodologies = relationship(
        "Methodology", back_populates="domain", cascade="all, delete-orphan"
    )
    relationships = relationship(
        "Relationship", back_populates="domain", cascade="all, delete-orphan"
    )

    # Add the relationship to DomainConfig
    configurations = relationship(
        "DomainConfig", back_populates="domain", cascade="all, delete-orphan"
    )

    # Relationship to user
    owner = relationship("User", back_populates="domains")


# Concept Model
class Concept(Base):
    __tablename__ = "concepts"

    concept_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True), ForeignKey("domains.domain_id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50))  # 'definition', 'process', 'methodology', etc.
    embedding = Column(Vector(1536))  # Using custom Vector type with dimension 1536
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # Relationship with Domain
    domain = relationship("Domain", back_populates="concepts")


# Source Model
class Source(Base):
    __tablename__ = "sources"

    source_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True), ForeignKey("domains.domain_id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    source_type = Column(String(50))  # 'table', 'api', etc.
    location = Column(Text, nullable=False)  # URI, table name, or connection string
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship with Domain
    domain = relationship("Domain", back_populates="sources")


# Methodology Model
class Methodology(Base):
    __tablename__ = "methodologies"

    methodology_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
    domain_id = Column(
        UUIDType(as_uuid=True), ForeignKey("domains.domain_id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    steps = Column(
        Text, nullable=False
    )  # Detailed steps on how to join sources or get data
    created_at = Column(TIMESTAMP, default=func.now())

    # Relationship with Domain
    domain = relationship("Domain", back_populates="methodologies")


# Relationship Model
class Relationship(Base):
    __tablename__ = "relationships"

    relationship_id = Column(
        UUIDType(as_uuid=True), primary_key=True, default=gen_random_uuid
    )
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

    # Relationship with Domain
    domain_id = Column(UUIDType(as_uuid=True), ForeignKey("domains.domain_id"))
    domain = relationship("Domain", back_populates="relationships")


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
