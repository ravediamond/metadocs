from src.db.rds import get_db_connection, commit_and_close
from src.models.schemas import UserSettings


# Get user settings
def get_user_settings(user_id: str) -> list[UserSettings]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, setting_key, setting_value, created_at, updated_at
                FROM user_settings
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            settings = cur.fetchall()

            return [
                UserSettings(
                    user_id=setting[0],
                    setting_key=setting[1],
                    setting_value=setting[2],
                    created_at=setting[3],
                    updated_at=setting[4],
                )
                for setting in settings
            ]
    except Exception as e:
        print(f"Error querying user settings: {str(e)}")
        return []
    finally:
        conn.close()


# Create or update a user setting
def create_or_update_user_setting(
    user_id: str, setting_key: str, setting_value: str
) -> UserSettings:
    now = datetime.utcnow()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_settings (user_id, setting_key, setting_value, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at;
                """,
                (user_id, setting_key, setting_value, now, now),
            )
        commit_and_close(conn)

        return UserSettings(
            user_id=user_id,
            setting_key=setting_key,
            setting_value=setting_value,
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        print(f"Error creating or updating user setting: {str(e)}")
        return None
