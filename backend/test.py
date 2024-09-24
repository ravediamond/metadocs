import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Example password and hashed password from your logs
plain_password = "password2"  # Replace with actual printed value
new_hashed = hash_password(plain_password)
print(new_hashed)
