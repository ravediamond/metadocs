from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from uuid import UUID

from ..models.models import (
    Domain,
    DomainVersion,
    Tenant,
    gen_random_uuid,
)
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainDataSchema,
    DomainSaveSchema,
)
from ..core.database import get_db  # Assuming you have a function to get the DB session

# Import to interact with PostgreSQL
from sqlalchemy import text

router = APIRouter()


# Utility function to create a graph in Apache AGE
def create_graph(db: Session, graph_name: str):
    try:
        create_graph_sql = text(f"SELECT ag_catalog.create_graph('{graph_name}');")
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

    # Get latest version of the domain
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
    concepts_query = text(
        f"SELECT * FROM cypher('{latest_version.graph_name}', $$ MATCH (n:Entity) RETURN n $$) as (v agtype);"
    )
    relationships_query = text(
        f"SELECT * FROM cypher('{latest_version.graph_name}', $$ MATCH ()-[r:Relationship]->() RETURN r $$) as (v agtype);"
    )

    try:
        concepts_result = db.execute(concepts_query).fetchall()
        relationships_result = db.execute(relationships_query).fetchall()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")

    # Process the results to extract data
    concepts = []
    for row in concepts_result:
        entity = row[0]["n"]  # Extract the 'n' node from the agtype
        concepts.append(
            {
                "id": entity.get("id"),
                "name": entity.get("name"),
                "type": entity.get("type"),
                "description": entity.get("description"),
                "metadata": entity.get("metadata"),
                "vector": entity.get("vector"),
                "created_at": entity.get("created_at"),
            }
        )

    relationships = []
    for row in relationships_result:
        relationship = row[0]["r"]  # Extract the 'r' relationship from the agtype
        relationships.append(
            {
                "name": relationship.get("name"),
                "type": relationship.get("type"),
                "description": relationship.get("description"),
                "metadata": relationship.get("metadata"),
                "vector": relationship.get("vector"),
                "created_at": relationship.get("created_at"),
                "from_entity_id": relationship.get(
                    "from"
                ),  # Adjust based on actual graph schema
                "to_entity_id": relationship.get(
                    "to"
                ),  # Adjust based on actual graph schema
            }
        )

    # Structure the domain data
    domain_data = DomainDataSchema(
        domain_id=domain.domain_id,
        domain_name=domain.domain_name,
        description=domain.description,
        tenant_id=tenant_id,
        version=latest_version.version,
        created_at=domain.created_at,
        concepts=concepts,
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
    # Use parameterized queries to prevent Cypher injection
    for entity in domain_data.concepts:
        create_entity_sql = text(
            """
            SELECT * FROM cypher(:graph_name, $$
                CREATE (:Entity {
                    id: :id,
                    name: :name,
                    type: :type,
                    description: :description,
                    metadata: :metadata,
                    vector: :vector,
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
                    "metadata": entity.metadata,
                    "vector": entity.vector,
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
                    name: :name,
                    type: :type,
                    description: :description,
                    metadata: :metadata,
                    vector: :vector,
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
                    "from_id": str(relationship.from_entity_id),
                    "to_id": str(relationship.to_entity_id),
                    "name": relationship.name,
                    "type": relationship.type,
                    "description": relationship.description,
                    "metadata": relationship.metadata,
                    "vector": relationship.vector,
                    "created_at": relationship.created_at,
                },
            )
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create relationship: {str(e)}"
            )

    db.commit()

    # Optionally, retrieve and return the newly saved domain data
    # This can be similar to the get_domain_details endpoint
    return get_domain_details(tenant_id, domain_id, db)
