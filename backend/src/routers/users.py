from fastapi import APIRouter, Depends
from auth.auth0 import get_current_user
from models.schemas import User
from db.dynamodb import users_table

router = APIRouter()

@router.get("/me", response_model=User)
async def get_current_user_info(current_user=Depends(get_current_user)):
    # Extract user info from token
    user_id = current_user["sub"]
    email = current_user.get("email")
    name = current_user.get("name")
    
    # Optionally, you can fetch additional data from the UsersTable
    # For now, we'll assume the token contains all needed info
    
    return User(user_id=user_id, email=email, name=name)