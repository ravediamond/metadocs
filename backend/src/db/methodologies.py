from uuid import uuid4
from src.db.rds import get_db_connection, commit_and_close
from src.models.schemas import Methodology


# Get all methodologies for a specific domain
def get_methodologies_by_domain(domain_id: str) -> list[Methodology]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT methodology_id, domain_id, name, description, steps, created_at
                FROM methodologies
                WHERE domain_id = %s;
                """,
                (domain_id,),
            )
            methodologies = cur.fetchall()

            return [
                Methodology(
                    methodology_id=methodology[0],
                    domain_id=methodology[1],
                    name=methodology[2],
                    description=methodology[3],
                    steps=methodology[4],
                    created_at=methodology[5],
                )
                for methodology in methodologies
            ]
    except Exception as e:
        print(f"Error querying methodologies by domain: {str(e)}")
        return []
    finally:
        conn.close()


# Create a new methodology
def create_methodology(
    domain_id: str, name: str, description: str, steps: str
) -> Methodology:
    methodology_id = str(uuid4())
    now = datetime.utcnow()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO methodologies (methodology_id, domain_id, name, description, steps, created_at)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (methodology_id, domain_id, name, description, steps, now),
            )
        commit_and_close(conn)

        return Methodology(
            methodology_id=methodology_id,
            domain_id=domain_id,
            name=name,
            description=description,
            steps=steps,
            created_at=now,
        )
    except Exception as e:
        print(f"Error creating methodology: {str(e)}")
        return None
