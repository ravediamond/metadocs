import os
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from ..models.models import User, APIKey
from ..core.database import get_db

# Get the secret key from the environment variable
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer to extract token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

http_bearer = HTTPBearer(auto_error=False)


# Password Hashing and Verification
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# JWT Token Creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Dependency to get the current authenticated user
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Fetch the user from the database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


def get_user_from_api_key(api_key: str, db: Session):
    api_key_obj = (
        db.query(APIKey)
        .filter(APIKey.api_key == api_key, APIKey.revoked == None)
        .first()
    )
    if not api_key_obj:
        return None
    return db.query(User).filter(User.user_id == api_key_obj.user_id).first()


async def get_current_user_or_api_key(
    request: Request,
    token: HTTPAuthorizationCredentials = Security(
        http_bearer
    ),  # Security now uses http_bearer without auto_error
    db: Session = Depends(get_db),
) -> User:
    # Check for X-API-Key in headers first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        user = get_user_from_api_key(api_key, db)
        if not user:
            raise HTTPException(status_code=403, detail="Invalid or revoked API key")
        return user

    # If no API key, fallback to token-based auth
    if token:
        # Extract the token credentials (the actual token string) and pass to `get_current_user`
        return get_current_user(token.credentials, db)

    raise HTTPException(status_code=401, detail="Unauthorized")
