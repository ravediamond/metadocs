from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from uuid import UUID

from ..core.database import get_db
from ..core.security import verify_password, get_password_hash, create_access_token
from ..models.models import User, Tenant, UserTenant, Role
from ..models.schemas import UserCreate, UserLogin, Token
from ..core.config import SYSTEM_MODE

router = APIRouter()


@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Tenant handling based on system mode
    if SYSTEM_MODE == "open_source":
        # Assign user to default tenant
        default_tenant = (
            db.query(Tenant).filter(Tenant.tenant_name == "Default").first()
        )
        if not default_tenant:
            default_tenant = Tenant(tenant_name="Default")
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)
        # Assign default role
        default_role = (
            db.query(Role)
            .filter(
                Role.role_name == "User", Role.tenant_id == default_tenant.tenant_id
            )
            .first()
        )
        if not default_role:
            default_role = Role(role_name="User", tenant_id=default_tenant.tenant_id)
            db.add(default_role)
            db.commit()
            db.refresh(default_role)
        user_tenant = UserTenant(
            user_id=new_user.user_id,
            tenant_id=default_tenant.tenant_id,
            role_id=default_role.role_id,
        )
        db.add(user_tenant)
        db.commit()
    elif SYSTEM_MODE == "saas":
        # Create a new tenant for the user
        new_tenant = Tenant(tenant_name=f"{new_user.name}'s Tenant")
        db.add(new_tenant)
        db.commit()
        db.refresh(new_tenant)
        # Create and assign owner role
        owner_role = Role(role_name="Owner", tenant_id=new_tenant.tenant_id)
        db.add(owner_role)
        db.commit()
        db.refresh(owner_role)
        user_tenant = UserTenant(
            user_id=new_user.user_id,
            tenant_id=new_tenant.tenant_id,
            role_id=owner_role.role_id,
        )
        db.add(user_tenant)
        db.commit()
    elif SYSTEM_MODE == "commercial":
        # In commercial mode, tenant assignment may be handled differently
        # For example, an admin might assign the user to a tenant
        pass

    # Create JWT token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_login.email).first()
    if not user or not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Get tenant IDs the user belongs to
    user_tenants = db.query(UserTenant).filter(UserTenant.user_id == user.user_id).all()
    tenant_ids = [str(ut.tenant_id) for ut in user_tenants]

    # Create JWT token including tenant_ids
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email, "tenant_ids": tenant_ids},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}
