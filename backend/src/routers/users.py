from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.auth.jwt import get_current_user  # Assuming JWT dependency
from src.db.users import get_user_by_email  # Import your DB helper function

router = APIRouter()


# Pydantic response model
class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    created_at: str  # created_at should be a string


# /users/me route
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    email = current_user["email"]

    # Fetch the user from the database using email
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert created_at (datetime) to an ISO string before returning
    user["CreatedAt"] = user["CreatedAt"].isoformat()

    return {
        "user_id": user["UserId"],
        "email": user["Email"],
        "name": user["Name"],
        "created_at": user["CreatedAt"],  # This is now an ISO-formatted string
    }
