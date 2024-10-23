import os
import psycopg2
import logging
import json
import re  # Import the regex module
from psycopg2 import sql

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to clean the agtype string by removing type annotations
def clean_agtype_string(s):
    """
    Removes type annotations like ::vertex, ::edge, and ::path from the agtype string.
    """
    # Remove '::vertex', '::edge', '::path'
    s = re.sub(r"::(vertex|edge|path)", "", s)
    return s


# Apache AGE requires setting up the search_path to include ag_catalog
def get_connection():
    """
    Establishes and returns a connection to the PostgreSQL database with Apache AGE.
    """
    POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "adminpassword")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "db")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            options="-c search_path=public,ag_catalog",
        )
        logger.info("Database connection established.")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        raise


def setup_age(conn, graph_name):
    """
    Sets up the AGE extension and creates a graph if it does not exist.
    """
    try:
        with conn.cursor() as cursor:
            # Enable the AGE extension if not already enabled
            cursor.execute("CREATE EXTENSION IF NOT EXISTS age;")
            logger.info("AGE extension ensured.")

            # Set the graph name
            cursor.execute('SET search_path = ag_catalog, "$user", public;')
            logger.info(f"Search path set for graph operations.")

            # Create the graph if it does not exist
            cursor.execute(
                sql.SQL("SELECT graphid FROM ag_graph WHERE name = %s;"), [graph_name]
            )
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("SELECT create_graph(%s);"), [graph_name])
                logger.info(f"Graph '{graph_name}' created.")
            else:
                logger.info(f"Graph '{graph_name}' already exists.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error setting up AGE: {e}")
        raise


def create_dummy_entities(conn, graph_name):
    """
    Creates dummy entity nodes in the specified graph.
    """
    try:
        with conn.cursor() as cursor:
            # Define Cypher queries to create nodes
            queries = [
                """
                CREATE (n:Person {name: 'Joe', title: 'Developer'})
                """,
                """
                CREATE (n:Person {name: 'Smith', title: 'Developer'})
                """,
                """
                CREATE (n:Person {name: 'Tom', title: 'Manager'})
                """,
            ]

            for query in queries:
                cursor.execute(
                    """
                    SELECT * FROM cypher(%s, $$ %s $$) AS (v agtype);
                """
                    % ("%s", query),
                    [graph_name],
                )
                logger.info("Entity created.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating dummy entities: {e}")
        raise


def create_dummy_relationships(conn, graph_name):
    """
    Creates dummy relationships between the entity nodes in the specified graph.
    """
    try:
        with conn.cursor() as cursor:
            # Define Cypher queries to create relationships
            queries = [
                """
                MATCH (a:Person {name: 'Joe'}), (b:Person {name: 'Smith'})
                CREATE (a)-[r:WORK_WITH {weight: 5}]->(b)
                """,
                """
                MATCH (a:Person {name: 'Smith'}), (b:Person {name: 'Tom'})
                CREATE (a)-[r:WORK_WITH {weight: 3}]->(b)
                """,
            ]

            for query in queries:
                cursor.execute(
                    """
                    SELECT * FROM cypher(%s, $$ %s $$) AS (v agtype);
                """
                    % ("%s", query),
                    [graph_name],
                )
                logger.info("Relationship created.")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating dummy relationships: {e}")
        raise


def query_graph(conn, graph_name):
    """
    Queries the graph to verify the created nodes and relationships.
    Enhanced to print detailed information about vertices and paths.
    """
    try:
        with conn.cursor() as cursor:
            # Query vertices
            logger.info("------- [Select Vertices] --------")
            cursor.execute(
                """
                SELECT * FROM cypher(%s, $$ MATCH (n) RETURN n $$) AS (v agtype);
            """,
                (graph_name,),
            )
            vertices = cursor.fetchall()
            for row in vertices:
                vertex_str = row[0]
                vertex_str_clean = clean_agtype_string(vertex_str)  # Clean the string
                try:
                    vertex = json.loads(vertex_str_clean)  # Parse the JSON string
                except json.JSONDecodeError as je:
                    logger.error(
                        f"JSON decoding failed for vertex: {vertex_str} | Error: {je}"
                    )
                    continue

                # Extract properties
                vertex_id = vertex.get("id", "N/A")
                vertex_label = vertex.get("label", "N/A")
                vertex_properties = vertex.get("properties", {})
                name = vertex_properties.get("name", "N/A")
                title = vertex_properties.get("title", "N/A")
                logger.info(
                    f"Vertex ID: {vertex_id}, Label: {vertex_label}, Name: {name}, Title: {title}"
                )
                logger.debug(f"Full Vertex Data: {vertex}")

            # Query paths
            logger.info("------- [Select Paths] --------")
            cursor.execute(
                """
                SELECT * FROM cypher(%s, $$ MATCH p=()-[]->() RETURN p LIMIT 10 $$) AS (v agtype);
            """,
                (graph_name,),
            )
            paths = cursor.fetchall()
            for row in paths:
                path_str = row[0]
                path_str_clean = clean_agtype_string(path_str)  # Clean the string
                try:
                    path = json.loads(path_str_clean)  # Parse the JSON string
                except json.JSONDecodeError as je:
                    logger.error(
                        f"JSON decoding failed for path: {path_str} | Error: {je}"
                    )
                    continue

                if path:
                    elements = path  # path is a list
                    if len(elements) >= 3:
                        v1 = elements[0]
                        e1 = elements[1]
                        v2 = elements[2]
                        # Extract properties
                        v1_label = v1.get("label", "N/A")
                        v1_props = v1.get("properties", {})
                        v1_name = v1_props.get("name", "N/A")

                        e1_label = e1.get("label", "N/A")
                        e1_props = e1.get("properties", {})
                        e1_weight = e1_props.get("weight", "N/A")

                        v2_label = v2.get("label", "N/A")
                        v2_props = v2.get("properties", {})
                        v2_name = v2_props.get("name", "N/A")

                        logger.info(
                            f"{v1_label}({v1_name}) -[{e1_label} weight:{e1_weight}]-> {v2_label}({v2_name})"
                        )
                        logger.debug(f"Full Path Data: {path}")
    except Exception as e:
        logger.error(f"Error querying the graph: {e}")
        raise


def main():
    GRAPH_NAME = "test_graph_v2"
    conn = None
    try:
        conn = get_connection()
        setup_age(conn, GRAPH_NAME)
        create_dummy_entities(conn, GRAPH_NAME)
        create_dummy_relationships(conn, GRAPH_NAME)
        query_graph(conn, GRAPH_NAME)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    main()
