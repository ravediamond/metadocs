import uuid
from datetime import datetime
from src.utils.security import hash_password
from src.db.rds import get_db_connection, commit_and_close


# Create a new user
def create_user(email: str, hashed_password: str, name: str) -> dict:
    user_id = str(uuid.uuid4())  # Generate unique user_id
    now = datetime.utcnow().isoformat()

    user_item = {
        "UserId": user_id,
        "Email": email,
        "HashedPassword": hashed_password,
        "Name": name,
        "CreatedAt": now,
    }

    try:
        # Insert user into the PostgreSQL database
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Print hashed password before inserting it

            cur.execute(
                """
                INSERT INTO users (UserId, Email, HashedPassword, Name, CreatedAt)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (user_id, email, hashed_password, name, now),
            )
        commit_and_close(conn)
        return user_item
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return None


def get_user_by_email(email: str):
    try:
        # Query the PostgreSQL database by Email
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT UserId, Email, HashedPassword, Name, CreatedAt
                FROM users
                WHERE Email = %s;
                """,
                (email,),
            )
            user = cur.fetchone()  # Fetch one user
            if user:
                # Print the hashed password retrieved from the database
                return {
                    "UserId": user[0],
                    "Email": user[1],
                    "HashedPassword": user[2],
                    "Name": user[3],
                    "CreatedAt": user[4],
                }
        return None  # No user found
    except Exception as e:
        print(f"Error querying user by email: {str(e)}")
        return None
    finally:
        conn.close()
