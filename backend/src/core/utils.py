import uuid
import secrets


def generate_uuid():
    return uuid.uuid4()


def generate_api_key(length=64):
    """Generate a secure random API key."""
    return secrets.token_hex(length // 2)
