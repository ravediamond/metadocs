from uuid import uuid4
from src.db.rds import get_db_connection, commit_and_close
from src.models.schemas import Source


# Get all sources for a specific domain
def get_sources_by_domain(domain_id: str) -> list[Source]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source_id, domain_id, name, source_type, location, description, created_at
                FROM sources
                WHERE domain_id = %s;
                """,
                (domain_id,),
            )
            sources = cur.fetchall()

            return [
                Source(
                    source_id=source[0],
                    domain_id=source[1],
                    name=source[2],
                    source_type=source[3],
                    location=source[4],
                    description=source[5],
                    created_at=source[6],
                )
                for source in sources
            ]
    except Exception as e:
        print(f"Error querying sources by domain: {str(e)}")
        return []
    finally:
        conn.close()


# Create a new source
def create_source(
    domain_id: str, name: str, source_type: str, location: str, description: str
) -> Source:
    source_id = str(uuid4())
    now = datetime.utcnow()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources (source_id, domain_id, name, source_type, location, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (source_id, domain_id, name, source_type, location, description, now),
            )
        commit_and_close(conn)

        return Source(
            source_id=source_id,
            domain_id=domain_id,
            name=name,
            source_type=source_type,
            location=location,
            description=description,
            created_at=now,
        )
    except Exception as e:
        print(f"Error creating source: {str(e)}")
        return None
