from src.db.rds import get_db_connection
from src.models.schemas import Domain  # Import the Domain Pydantic model


# Get all domains for a specific owner
def get_domains_by_owner(user_id: str) -> list[Domain]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT domain_id, domain_name, owner_user_id, description, created_at
                FROM domains
                WHERE owner_user_id = %s;
                """,
                (user_id,),
            )
            domains = cur.fetchall()

            # Map the result to a list of Domain Pydantic models
            return [
                Domain(
                    domain_id=domain[0],
                    domain_name=domain[1],
                    owner_user_id=domain[2],
                    description=domain[3],
                    created_at=domain[4],
                )
                for domain in domains
            ]
    except Exception as e:
        print(f"Error querying domains by owner: {str(e)}")
        return []
    finally:
        conn.close()
