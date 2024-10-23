import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables for the database
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "adminpassword")
POSTGRES_DB = os.getenv("POSTGRES_DB", "db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Create the DATABASE_URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL, connect_args={"options": "-csearch_path=public,ag_catalog"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_properties(properties: dict) -> str:
    """
    Converts a dictionary of properties into a Cypher-compatible property string.
    Ensures proper escaping of quotes and formatting.
    """
    prop_strings = []
    for key, value in properties.items():
        if isinstance(value, str):
            # Escape single quotes in string values
            value = value.replace("'", "\\'")
            prop_strings.append(f"{key}: '{value}'")
        elif isinstance(value, list):
            # Convert list to Cypher list syntax
            list_items = ", ".join(map(str, value))
            prop_strings.append(f"{key}: [{list_items}]")
        elif isinstance(value, dict):
            # Convert dict to JSON string and escape quotes
            json_str = json.dumps(value).replace("'", "\\'")
            prop_strings.append(f"{key}: '{json_str}'")
        else:
            # For numeric and other types
            prop_strings.append(f"{key}: {value}")
    return ", ".join(prop_strings)


# Utility function to create a graph in Apache AGE
def create_graph(db: Session, graph_name: str):
    try:
        # Use f-string to inject graph_name directly into the query
        create_graph_sql = text(
            f"SELECT * FROM ag_catalog.create_graph('{graph_name}');"
        )
        db.execute(create_graph_sql)
        db.commit()
        logger.info(f"Graph '{graph_name}' created successfully.")
    except SQLAlchemyError as e:
        db.rollback()
        if "already exists" in str(e):
            logger.info(f"Graph '{graph_name}' already exists.")
            pass  # Ignore if the graph already exists
        else:
            logger.error(f"Graph creation failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Graph creation failed: {str(e)}"
            )


# Utility function to add a test entity with dynamic properties
def add_entity(db: Session, graph_name: str, properties: dict):
    try:
        # Build the properties string from the dictionary
        props_str = build_properties(properties)

        # Enclose the label in backticks to prevent colon misinterpretation
        create_entity_sql = text(
            f"""
            SELECT * FROM cypher('{graph_name}', $$
                CREATE (`Entity` {{
                    {props_str}
                }})
            $$) AS (v agtype);
            """
        )
        # Optional: Print the final query for debugging purposes
        # print("Entity Query:", create_entity_sql.text)

        db.execute(create_entity_sql)
        db.commit()
        logger.info("Test entity added successfully.")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create test entity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create test entity: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while creating test entity: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating test entity.",
        )


# Utility function to add a test relationship with dynamic properties
def add_relationship(db: Session, graph_name: str, properties: dict):
    try:
        # Build the properties string from the dictionary
        props_str = build_properties(properties)

        from_name = properties.get("from_name", "test_name")
        to_name = properties.get("to_name", "test_name")

        # Enclose the relationship type in backticks to prevent colon misinterpretation
        create_relationship_sql = text(
            f"""
            SELECT * FROM cypher('{graph_name}', $$
                MATCH (from:`Entity` {{name: '{from_name}'}}), 
                      (to:`Entity` {{name: '{to_name}'}})
                CREATE (from)-[:`Relationship` {{
                    {props_str}
                }}]->(to)
            $$) AS (v agtype);
            """
        )
        # Optional: Print the final query for debugging purposes
        # print("Relationship Query:", create_relationship_sql.text)

        db.execute(create_relationship_sql)
        db.commit()
        logger.info("Test relationship added successfully.")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create test relationship: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create test relationship: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error while creating test relationship: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating test relationship.",
        )


# Main function to test graph creation, entity, and relationship insertion
def main():
    print("#### Starting the script ####")
    db_generator = get_db()
    db = next(db_generator)  # Get the database session

    graph_name = "test_v3"  # You can change this as needed

    # Create the graph
    create_graph(db, graph_name)

    # Define properties for the test entity
    entity_properties = {
        "name": "test_name1",
        "type": "test_type",
        "description": "test_description",
        "vector": [0.1, 0.2, 0.3, 0.4],
        "metadata": {"key": "value"},
        "version": 1,
        "created_at": "2024-04-27T00:00:00Z",
    }

    # Add a test entity with dynamic properties
    add_entity(db, graph_name, entity_properties)

    entity_properties = {
        "name": "test_name2",
        "type": "test_type",
        "description": "test_description",
        "vector": [0.1, 0.2, 0.3, 0.4],
        "metadata": {"key": "value"},
        "version": 1,
        "created_at": "2024-04-27T00:00:00Z",
    }

    # Add a test entity with dynamic properties
    add_entity(db, graph_name, entity_properties)

    # Define properties for the test relationship
    relationship_properties = {
        "type": "test_relationship",
        "vector": [0.1, 0.2, 0.3, 0.4],
        "metadata": {"key": "value"},
        "version": 1,
        "created_at": "2024-04-27T00:00:00Z",
        "from_name": "test_name1",  # Optional: specify source node name
        "to_name": "test_name2",  # Optional: specify target node name
    }

    # Add a test relationship with dynamic properties
    add_relationship(db, graph_name, relationship_properties)

    print("#### Test entity and relationship added successfully ####")


if __name__ == "__main__":
    main()
