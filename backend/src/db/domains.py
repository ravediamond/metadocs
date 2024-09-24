from src.db.rds import get_db_connection


# Get all domains for a specific owner
def get_domains_by_owner(user_id: str):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DomainId, DomainName, OwnerUserId, Description, CreatedAt
                FROM domains
                WHERE OwnerUserId = %s;
                """,
                (user_id,),
            )
            domains = cur.fetchall()
            return [
                {
                    "DomainId": domain[0],
                    "DomainName": domain[1],
                    "OwnerUserId": domain[2],
                    "Description": domain[3],
                    "CreatedAt": domain[4],
                }
                for domain in domains
            ]
    except Exception as e:
        print(f"Error querying domains by owner: {str(e)}")
        return []
    finally:
        conn.close()
