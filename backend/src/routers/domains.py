from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from uuid import UUID
import json

from ..models.models import Domain, DomainVersion, Tenant, gen_random_uuid
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainDataSchema,
    DomainSaveSchema,
)
from ..core.database import get_db

from sqlalchemy import text

router = APIRouter()


# Utility function to create a graph in Apache AGE
def create_graph(db: Session, graph_name: str):
    try:
        create_graph_sql = text(f"SELECT create_graph('{graph_name}');")
        db.execute(create_graph_sql)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        if "already exists" in str(e):
            pass  # Ignore if the graph already exists
        else:
            raise HTTPException(
                status_code=500, detail=f"Graph creation failed: {str(e)}"
            )


@router.post("/tenants/{tenant_id}/domains", response_model=DomainSchema)
def create_domain(
    tenant_id: UUID, domain_data: DomainCreate, db: Session = Depends(get_db)
):
    # Ensure the tenant exists
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Create the new domain
    new_domain = Domain(
        tenant_id=tenant_id,
        domain_name=domain_data.domain_name,
        description=domain_data.description,
        owner_user_id=domain_data.owner_user_id,
    )

    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    # Create the initial version for this domain
    new_domain_version = DomainVersion(
        domain_id=new_domain.domain_id,
        tenant_id=tenant_id,
        version=1,
        graph_name=f"{new_domain.domain_id}_v1",
    )

    db.add(new_domain_version)
    db.commit()
    db.refresh(new_domain_version)

    # Create a graph in Apache AGE for this domain version
    create_graph(db, new_domain_version.graph_name)

    return new_domain


@router.get("/tenants/{tenant_id}/domains", response_model=List[DomainSchema])
def get_domains(tenant_id: UUID, db: Session = Depends(get_db)):
    # Ensure the tenant exists
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Query for all domains related to this tenant
    domains = db.query(Domain).filter(Domain.tenant_id == tenant_id).all()

    return domains


@router.get("/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainDataSchema)
def get_domain_details(tenant_id: UUID, domain_id: UUID, db: Session = Depends(get_db)):
    # Ensure the domain exists within the tenant
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get the latest version of the domain
    latest_version = (
        db.query(DomainVersion)
        .filter(
            DomainVersion.domain_id == domain_id, DomainVersion.tenant_id == tenant_id
        )
        .order_by(DomainVersion.version.desc())
        .first()
    )

    if not latest_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    # Retrieve the entities and relationships from the graph
    entities_query = text(
        f"SELECT * FROM cypher('{latest_version.graph_name}', $$ MATCH (n:Entity) RETURN n $$) as (v agtype);"
    )
    relationships_query = text(
        f"SELECT * FROM cypher('{latest_version.graph_name}', $$ MATCH ()-[r:Relationship]->() RETURN r $$) as (v agtype);"
    )

    try:
        entities_result = db.execute(entities_query).fetchall()
        relationships_result = db.execute(relationships_query).fetchall()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")

    # Process the results to extract data
    entities = []
    for row in entities_result:
        try:
            entity_str = row[0].split("::vertex")[0].strip()  # Get the JSON part
            entity_data = json.loads(entity_str)  # Parse the JSON
            properties = entity_data.get("properties", {})
            print(properties)
            entities.append(
                {
                    "id": str(entity_data.get("id")),
                    "name": properties.get("name"),
                    "type": properties.get("type"),
                    "description": properties.get("description"),
                    "metadata": json.loads(properties.get("metadata")),
                    "version": latest_version.version,
                    "created_at": properties.get("created_at"),
                }
            )
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Error parsing entity data: {e}")
            continue

    relationships = []
    for row in relationships_result:
        try:
            relationship_str = row[0].split("::edge")[0].strip()  # Get the JSON part
            relationship_data = json.loads(relationship_str)
            properties = relationship_data.get("properties", {})
            print(properties)
            print(relationship_data.get("start_id"))
            print(relationship_data.get("end_id"))
            relationships.append(
                {
                    "id": str(relationship_data.get("id")),
                    "from_entity_id": str(relationship_data.get("start_id")),
                    "to_entity_id": str(relationship_data.get("end_id")),
                    "name": properties.get("name"),
                    "type": properties.get("type"),
                    "description": properties.get("description"),
                    "metadata": json.loads(properties.get("metadata")),
                    "version": latest_version.version,
                    "created_at": properties.get("created_at"),
                }
            )
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Error parsing relationship data: {e}")
            continue

    # Structure the domain data
    domain_data = DomainDataSchema(
        domain_id=domain.domain_id,
        domain_name=domain.domain_name,
        description=domain.description,
        tenant_id=tenant_id,
        version=latest_version.version,
        created_at=domain.created_at,
        entities=entities,
        relationships=relationships,
    )

    return domain_data


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/save", response_model=DomainDataSchema
)
def save_domain(
    tenant_id: UUID,
    domain_id: UUID,
    domain_data: DomainSaveSchema,
    db: Session = Depends(get_db),
):
    # Ensure the domain exists within the tenant
    domain = (
        db.query(Domain)
        .filter(Domain.tenant_id == tenant_id, Domain.domain_id == domain_id)
        .first()
    )
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get the latest domain version
    latest_version = (
        db.query(DomainVersion)
        .filter(
            DomainVersion.domain_id == domain_id, DomainVersion.tenant_id == tenant_id
        )
        .order_by(DomainVersion.version.desc())
        .first()
    )

    if not latest_version:
        raise HTTPException(status_code=404, detail="Domain version not found")

    # Increment the version
    new_version = latest_version.version + 1
    new_graph_name = f"{domain.domain_id}_v{new_version}"

    # Create a new DomainVersion for the updated domain
    new_domain_version = DomainVersion(
        domain_id=domain_id,
        tenant_id=tenant_id,
        version=new_version,
        graph_name=new_graph_name,
    )

    db.add(new_domain_version)
    db.commit()
    db.refresh(new_domain_version)

    # Create a graph for the new domain version
    create_graph(db, new_graph_name)

    # Save entities and relationships into the new graph
    for entity in domain_data.entities:
        create_entity_sql = text(
            """
            SELECT * FROM cypher(:graph_name, $$
                CREATE (:Entity {
                    id: :id,
                    name: :name,
                    type: :type,
                    description: :description,
                    metadata: :metadata,
                    version: :version,
                    created_at: :created_at
                })
            $$) as (v agtype);
            """
        )
        try:
            db.execute(
                create_entity_sql,
                {
                    "graph_name": new_graph_name,
                    "id": str(entity.id or gen_random_uuid()),
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description,
                    "metadata": (
                        json.dumps(entity.metadata) if entity.metadata else None
                    ),
                    "version": entity.version,
                    "created_at": entity.created_at,
                },
            )
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create entity: {str(e)}"
            )

    for relationship in domain_data.relationships:
        create_relationship_sql = text(
            """
            SELECT * FROM cypher(:graph_name, $$
                MATCH (from:Entity {id: :from_id}), (to:Entity {id: :to_id})
                CREATE (from)-[:Relationship {
                    id: :id,
                    type: :type,
                    metadata: :metadata,
                    version: :version,
                    created_at: :created_at
                }]->(to)
            $$) as (v agtype);
            """
        )
        try:
            db.execute(
                create_relationship_sql,
                {
                    "graph_name": new_graph_name,
                    "id": str(relationship.id or gen_random_uuid()),
                    "from_id": str(relationship.from_entity_id),
                    "to_id": str(relationship.to_entity_id),
                    "type": relationship.type,
                    "metadata": (
                        json.dumps(relationship.metadata)
                        if relationship.metadata
                        else None
                    ),
                    "version": relationship.version,
                    "created_at": relationship.created_at,
                },
            )
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create relationship: {str(e)}"
            )

    db.commit()

    # Retrieve and return the newly saved domain data
    return get_domain_details(tenant_id, domain_id, db)
