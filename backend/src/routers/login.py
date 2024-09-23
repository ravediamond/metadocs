from fastapi import APIRouter, HTTPException, Depends
from auth.jwt import create_access_token
from models.schemas import UserLogin
from db.users import get_user_by_email  # Example function to check user credentials

router = APIRouter()


@router.post("/login")
async def login(user_data: UserLogin):
    user = get_user_by_email(user_data.email)
    if not user or not user.verify_password(user_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token
    access_token = create_access_token(
        data={"user_id": user.user_id, "roles": user.roles}
    )
    return {"access_token": access_token, "token_type": "bearer"}
