import uuid
from datetime import datetime
from src.db.rds import get_db_connection, commit_and_close
from src.models.schemas import User  # Import the User schema


# Create a new user
def create_user(email: str, hashed_password: str, name: str) -> User:
    user_id = str(uuid.uuid4())  # Generate unique user_id
    now = datetime.utcnow()

    try:
        # Insert user into the PostgreSQL database
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, email, hashed_password, name, created_at)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (user_id, email, hashed_password, name, now),
            )
        commit_and_close(conn)

        # Return the created user as a Pydantic model (User)
        return User(
            user_id=user_id,
            email=email,
            hashed_password=hashed_password,
            name=name,
            created_at=now,
        )
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return None


def get_user_by_email(email: str) -> User:
    try:
        # Query the PostgreSQL database by email
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, email, hashed_password, name, created_at
                FROM users
                WHERE email = %s;
                """,
                (email,),
            )
            user = cur.fetchone()  # Fetch one user
            if user:
                # Return the fetched user as a Pydantic model (User)
                return User(
                    user_id=user[0],
                    email=user[1],
                    hashed_password=user[2],
                    name=user[3],
                    created_at=user[4],
                )
        return None  # No user found
    except Exception as e:
        print(f"Error querying user by email: {str(e)}")
        return None
    finally:
        conn.close()
