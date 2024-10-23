from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from uuid import UUID
import logging
import json
import re

import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.models import Domain, DomainVersion, Tenant, gen_random_uuid
from ..models.schemas import (
    Domain as DomainSchema,
    DomainCreate,
    DomainDataSchema,
    DomainSaveSchema,
)
from ..core.database import get_db, get_age_connection

from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter()


# Utility function to create a graph in Apache AGE using psycopg2
def create_graph_age(conn, graph_name: str):
    """
    Creates a graph in Apache AGE if it does not already exist.
    """
    try:
        with conn.cursor() as cursor:
            # Enable the AGE extension if not already enabled
            cursor.execute("CREATE EXTENSION IF NOT EXISTS age;")
            logger.info("AGE extension ensured.")

            # Set the search_path appropriately
            cursor.execute('SET search_path = ag_catalog, "$user", public;')
            logger.info("Search path set for Apache AGE.")

            # Check if the graph already exists
            cursor.execute(
                "SELECT graphid FROM ag_graph WHERE name = %s;", (graph_name,)
            )
            if cursor.fetchone() is None:
                cursor.execute("SELECT create_graph(%s);", (graph_name,))
                logger.info(f"Graph '{graph_name}' created in Apache AGE.")
            else:
                logger.info(f"Graph '{graph_name}' already exists in Apache AGE.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error setting up Apache AGE: {e}")
        raise HTTPException(status_code=500, detail=f"Graph setup failed: {str(e)}")


def clean_agtype_string(s):
    """
    Removes type annotations like ::vertex, ::edge, and ::path from the agtype string.
    """
    # Remove '::vertex', '::edge', '::path', etc.
    return re.sub(r"::\w+", "", s)


def execute_cypher_query(conn, graph_name: str, cypher_query: str):
    """
    Executes a Cypher query on the specified Apache AGE graph and returns parsed results.

    Args:
        conn: psycopg2 connection object.
        graph_name (str): Name of the graph in Apache AGE.
        cypher_query (str): The Cypher query to execute.

    Returns:
        List of parsed results (dicts for vertices/edges or lists for paths).

    Raises:
        HTTPException: If the query execution fails.
    """
    try:
        with conn.cursor() as cursor:
            # Prepare the formatted Cypher query
            formatted_query = f"""
                SELECT * FROM cypher('{graph_name}', $$
                    {cypher_query}
                $$) AS (v agtype);
            """
            logger.debug(f"Executing Cypher query: {formatted_query}")
            cursor.execute(formatted_query)
            rows = cursor.fetchall()
            logger.debug(f"Raw fetched rows: {rows}")

            # Initialize a list to hold parsed results
            parsed_rows = []

            for row in rows:
                v_str = row[0]  # Assuming 'v agtype' is the first column
                v_str_clean = clean_agtype_string(v_str)
                logger.debug(f"Cleaned 'v' string: {v_str_clean}")

                try:
                    parsed_v = json.loads(v_str_clean)
                    parsed_rows.append(parsed_v)
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decoding failed for v: {v_str} | Error: {je}")
                    continue  # Skip this row and continue with others

            logger.info(
                f"Executed Cypher query successfully. Number of rows fetched: {len(parsed_rows)}"
            )
            return parsed_rows
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to execute Cypher query: {e}")
        raise HTTPException(status_code=500, detail=f"Cypher query failed: {str(e)}")


@router.post("/tenants/{tenant_id}/domains", response_model=DomainSchema)
def create_domain(
    tenant_id: UUID, domain_data: DomainCreate, db: Session = Depends(get_db)
):
    """
    Creates a new domain and initializes its corresponding Apache AGE graph.
    """
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
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating new domain: {e}")
        raise HTTPException(status_code=500, detail="Failed to create domain")
    db.refresh(new_domain)

    # Create the initial version for this domain
    new_domain_version = DomainVersion(
        domain_id=new_domain.domain_id,
        tenant_id=tenant_id,
        version=1,
        graph_name=f"{new_domain.domain_id}_v1",
    )

    db.add(new_domain_version)
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating domain version: {e}")
        raise HTTPException(status_code=500, detail="Failed to create domain version")
    db.refresh(new_domain_version)

    # Create a graph in Apache AGE for this domain version using psycopg2
    try:
        with get_age_connection() as conn:
            create_graph_age(conn, new_domain_version.graph_name)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during graph creation: {e}")
        raise HTTPException(status_code=500, detail="Graph creation failed")

    return new_domain


@router.get("/tenants/{tenant_id}/domains", response_model=List[DomainSchema])
def get_domains(tenant_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves all domains associated with a specific tenant.
    """
    # Ensure the tenant exists
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Query for all domains related to this tenant
    domains = db.query(Domain).filter(Domain.tenant_id == tenant_id).all()

    return domains


@router.get("/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainDataSchema)
def get_domain_details(tenant_id: UUID, domain_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves detailed information about a specific domain, including its entities and relationships from Apache AGE.
    """
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

    # Retrieve the entities and relationships from the graph using psycopg2
    try:
        with get_age_connection() as conn:
            # Query entities
            entities_cypher = """
                MATCH (n:Entity) RETURN n
            """
            entities_result = execute_cypher_query(
                conn, latest_version.graph_name, entities_cypher
            )

            # Query relationships
            relationships_cypher = """
                MATCH ()-[r:Relationship]->() RETURN r
            """
            relationships_result = execute_cypher_query(
                conn, latest_version.graph_name, relationships_cypher
            )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during graph querying: {e}")
        raise HTTPException(status_code=500, detail="Graph query failed")

    # Process the results to extract data
    entities = []
    for row in entities_result:
        print("######")
        print(row)
        try:
            # agtype_data = row["v"]
            # entity = agtype_data.get("n")
            properties = row.get("properties", {})
            entities.append(
                {
                    "id": str(row.get("id")),
                    "name": properties.get("name"),
                    "type": properties.get("type"),
                    "description": properties.get("description"),
                    "metadata": properties.get("metadata", {}),
                    "version": latest_version.version,
                    "created_at": properties.get("created_at"),
                }
            )
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing entity data: {e}")
            continue

    relationships = []
    for row in relationships_result:
        print("######")
        print(row)
        try:
            # agtype_data = row["v"]
            # relationship = agtype_data.get("r")
            properties = row.get("properties", {})
            relationships.append(
                {
                    "id": str(row.get("id")),
                    "from_entity_id": str(row.get("start_id")),
                    "to_entity_id": str(row.get("end_id")),
                    "name": properties.get("name"),
                    "type": properties.get("type"),
                    "description": properties.get("description"),
                    "metadata": json.loads(properties.get("metadata", {})),
                    "version": latest_version.version,
                    "created_at": properties.get("created_at"),
                }
            )
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing relationship data: {e}")
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
    """
    Saves updates to a domain by creating a new version and updating entities and relationships in Apache AGE.
    """
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
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating new domain version: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create new domain version"
        )
    db.refresh(new_domain_version)

    # Create a graph for the new domain version using psycopg2
    try:
        with get_age_connection() as conn:
            create_graph_age(conn, new_graph_name)

            # Save entities into the new graph
            for entity in domain_data.entities:
                # Prepare the Cypher query with proper escaping
                create_entity_cypher = f"""
                    CREATE (n:Entity {{
                        id: '{str(entity.id).replace("'", "''")}',
                        name: '{entity.name.replace("'", "''")}',
                        type: '{entity.type.replace("'", "''")}',
                        description: '{entity.description.replace("'", "''")}',
                        metadata: '{json.dumps(entity.metadata).replace("'", "''")}'::json,
                        version: {new_version},
                        created_at: '{entity.created_at.isoformat() if entity.created_at else None}'
                    }})
                """
                try:
                    execute_cypher_query(conn, new_graph_name, create_entity_cypher)
                    logger.info(
                        f"Entity '{entity.name}' created in graph '{new_graph_name}'."
                    )
                except HTTPException as he:
                    raise he
                except Exception as e:
                    logger.error(f"Failed to create entity '{entity.name}': {e}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create entity '{entity.name}': {str(e)}",
                    )

            # Save relationships into the new graph
            for relationship in domain_data.relationships:
                # Prepare the Cypher query with proper escaping
                create_relationship_cypher = f"""
                    MATCH (a:Entity {{id: '{str(relationship.from_entity_id).replace("'", "''")}'}}), (b:Entity {{id: '{str(relationship.to_entity_id).replace("'", "''")}'}})
                    CREATE (a)-[r:Relationship {{
                        id: '{str(relationship.id).replace("'", "''")}',
                        name: '{relationship.name.replace("'", "''")}',
                        type: '{relationship.type.replace("'", "''")}',
                        description: '{relationship.description.replace("'", "''")}',
                        metadata: '{json.dumps(relationship.metadata).replace("'", "''")}'::json,
                        version: {new_version},
                        created_at: '{relationship.created_at.isoformat() if relationship.created_at else None}'
                    }}]->(b)
                """
                try:
                    execute_cypher_query(
                        conn, new_graph_name, create_relationship_cypher
                    )
                    logger.info(
                        f"Relationship '{relationship.name}' created in graph '{new_graph_name}'."
                    )
                except HTTPException as he:
                    raise he
                except Exception as e:
                    logger.error(
                        f"Failed to create relationship '{relationship.name}': {e}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create relationship '{relationship.name}': {str(e)}",
                    )

            # Commit all changes after successful insertion
            conn.commit()
            logger.info(
                f"All entities and relationships saved in graph '{new_graph_name}'."
            )
    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Graph operation failed: {e}")
        raise HTTPException(status_code=500, detail="Graph operation failed")
    except Exception as e:
        logger.error(f"Unexpected error during graph operations: {e}")
        raise HTTPException(status_code=500, detail="Graph operation failed")

    # Retrieve and return the newly saved domain data
    return get_domain_details(tenant_id, domain_id, db)
