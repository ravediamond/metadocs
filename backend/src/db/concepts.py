from uuid import uuid4
from src.db.rds import get_db_connection, commit_and_close
from src.models.schemas import Concept


# Get all concepts for a specific domain
def get_concepts_by_domain(domain_id: str) -> list[Concept]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT concept_id, domain_id, name, description, type, created_at, updated_at
                FROM concepts
                WHERE domain_id = %s;
                """,
                (domain_id,),
            )
            concepts = cur.fetchall()

            return [
                Concept(
                    concept_id=concept[0],
                    domain_id=concept[1],
                    name=concept[2],
                    description=concept[3],
                    type=concept[4],
                    created_at=concept[5],
                    updated_at=concept[6],
                )
                for concept in concepts
            ]
    except Exception as e:
        print(f"Error querying concepts by domain: {str(e)}")
        return []
    finally:
        conn.close()


# Create a new concept
def create_concept(
    domain_id: str, name: str, description: str, concept_type: str
) -> Concept:
    concept_id = str(uuid4())
    now = datetime.utcnow()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO concepts (concept_id, domain_id, name, description, type, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (concept_id, domain_id, name, description, concept_type, now, now),
            )
        commit_and_close(conn)

        return Concept(
            concept_id=concept_id,
            domain_id=domain_id,
            name=name,
            description=description,
            type=concept_type,
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        print(f"Error creating concept: {str(e)}")
        return None
