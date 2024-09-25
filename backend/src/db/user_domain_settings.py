from src.db.rds import get_db_connection, commit_and_close
from src.models.schemas import UserDomainSettings


# Get user domain-specific settings
def get_user_domain_settings(user_id: str, domain_id: str) -> list[UserDomainSettings]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, domain_id, setting_key, setting_value, created_at, updated_at
                FROM user_domain_settings
                WHERE user_id = %s AND domain_id = %s;
                """,
                (user_id, domain_id),
            )
            settings = cur.fetchall()

            return [
                UserDomainSettings(
                    user_id=setting[0],
                    domain_id=setting[1],
                    setting_key=setting[2],
                    setting_value=setting[3],
                    created_at=setting[4],
                    updated_at=setting[5],
                )
                for setting in settings
            ]
    except Exception as e:
        print(f"Error querying user domain-specific settings: {str(e)}")
        return []
    finally:
        conn.close()


# Create or update a user domain-specific setting
def create_or_update_user_domain_setting(
    user_id: str, domain_id: str, setting_key: str, setting_value: str
) -> UserDomainSettings:
    now = datetime.utcnow()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_domain_settings (user_id, domain_id, setting_key, setting_value, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, domain_id, setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at;
                """,
                (user_id, domain_id, setting_key, setting_value, now, now),
            )
        commit_and_close(conn)

        return UserDomainSettings(
            user_id=user_id,
            domain_id=domain_id,
            setting_key=setting_key,
            setting_value=setting_value,
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        print(f"Error creating or updating user domain-specific setting: {str(e)}")
        return None
