import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Example password and hashed password from your logs
plain_password = "Ravediamond6"  # Replace with actual printed value
hashed_password = "$2b$12$u2hkMkCDdZL3MILBDeCSxukbueUsHDDbFQhqs.ZjlI9FbLtX74F4."  # Replace with actual printed value
new_hashed = hash_password(plain_password)
print(new_hashed)

# Compare manually
print(bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8")))
print(bcrypt.checkpw(plain_password.encode("utf-8"), new_hashed.encode("utf-8")))


# $2b$12$NXtQIL/mokqWWCGpgJVJ9OJLn4X/A8EW9/ULZybIeb2KC5tHne5Ne
# $2b$12$q1LtYLbWrHE1yNcHCQULDOCLzMpe8boqUulmqvXM43vJVq/crpVO6
