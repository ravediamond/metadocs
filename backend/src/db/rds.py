import psycopg2
from os import getenv


# Create a function to get a PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host=getenv("POSTGRES_HOST"),
        database=getenv("POSTGRES_DB"),
        user=getenv("POSTGRES_USER"),
        password=getenv("POSTGRES_PASSWORD"),
        port=getenv("POSTGRES_PORT"),
    )


# Optionally, you can also add a function for committing changes and closing the connection
def commit_and_close(conn):
    conn.commit()
    conn.close()
