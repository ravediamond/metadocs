from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.auth.jwt import create_access_token
from src.db.users import get_user_by_email, create_user
from src.utils.security import verify_password, hash_password
from src.models.schemas import UserCreate, UserLogin

router = APIRouter()


# Pydantic models for request data validation


# Login route
@router.post("/login")
async def login(user_data: UserLogin):
    user = get_user_by_email(user_data.email)

    # Updated to access attributes using dot notation
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token using dot notation
    access_token = create_access_token(
        data={"sub": user.user_id, "email": user.email, "name": user.name}
    )

    return {"access_token": access_token, "token_type": "bearer"}


# Register route
@router.post("/register")
async def register(user_data: UserCreate):
    # Check if the user already exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists."
        )

    # Hash the user's password
    hashed_password = hash_password(user_data.password)

    # Create the user in the database
    create_user(user_data.email, hashed_password, user_data.name)

    return {"message": "User created successfully"}
