from fastapi import APIRouter, Depends
from auth.auth0 import get_current_user
from models.schemas import User
from auth.auth0 import get_current_user, require_roles

router = APIRouter()


@router.get("/me", response_model=User)
async def get_current_user_info(current_user=Depends(get_current_user)):
    user_id = current_user["sub"]
    email = current_user.get("email")
    name = current_user.get("name")
    return User(user_id=user_id, email=email, name=name)


@router.get("/admin/dashboard")
async def admin_dashboard(current_user=Depends(require_roles(["Admin"]))):
    return {"message": f"Welcome to the admin dashboard, {current_user.get('name')}!"}
