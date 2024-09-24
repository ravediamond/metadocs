import os
import jwt
from fastapi import HTTPException, Request, Depends, status
from datetime import datetime, timedelta
from typing import Dict
from jose import JWTError, jwt

# JWT Secret and algorithm (use a secure secret in production)
JWT_SECRET = os.getenv("JWT_SECRET")  # Set this in your environment
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token expiration time


# Create a JWT token
def create_access_token(data: Dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# Extract and verify JWT token from request
def get_token_auth_header(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = auth.split()
    if parts[0].lower() != "bearer" or len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    return parts[1]


# Verify the JWT token and return the decoded payload (user info)
def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# Dependency for FastAPI routes to retrieve the current user
async def get_current_user(request: Request):
    token = get_token_auth_header(request)
    payload = verify_token(token)
    return payload  # Payload contains user information (sub, email, name)
