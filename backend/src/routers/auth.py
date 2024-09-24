from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.auth.jwt import create_access_token
from src.db.users import get_user_by_email, create_user
from src.utils.security import verify_password, hash_password

router = APIRouter()


# Pydantic models for request data validation
class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    name: str


# Login route
@router.post("/login")
async def login(user_data: UserLogin):
    user = get_user_by_email(user_data.email)

    if not user or not verify_password(user_data.password, user["HashedPassword"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token
    access_token = create_access_token(
        data={"sub": user["UserId"], "email": user["Email"], "name": user["Name"]}
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
