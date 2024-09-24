from fastapi import APIRouter, Depends, HTTPException
from src.auth.jwt import get_current_user  # Assuming JWT dependency
from src.db.users import get_user_by_email  # Import your DB helper function
from src.models.schemas import UserResponse  # Import the UserResponse Pydantic model

router = APIRouter()


# /users/me route
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    email = current_user["email"]

    # Fetch the user from the database using email
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Pydantic model already handles datetime conversion, no need to format manually
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,  # Pydantic automatically converts this to ISO format
    }
